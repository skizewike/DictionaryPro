# core/views.py (ПОЛНОСТЬЮ)
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Word, Language, Category, WordProgress, Lesson, CompletedTest

@login_required
def dashboard(request):
    user = request.user
    now = timezone.now()
    
    total_words = WordProgress.objects.filter(user=user).count()
    mastered_words = WordProgress.objects.filter(user=user, mastered=True).count()
    
    due_for_review = WordProgress.objects.filter(
        user=user,
        mastered=False,
        next_review_date__lte=now
    ).count()
    
    lang_stats = []
    languages = Language.objects.all()
    for lang in languages:
        words_in_lang = Word.objects.filter(language=lang)
        total = words_in_lang.count()
        mastered = WordProgress.objects.filter(
            user=user,
            word__language=lang,
            mastered=True
        ).count()
        if total > 0:
            lang_stats.append({
                'language': lang,
                'total': total,
                'mastered': mastered,
                'percent': round((mastered / total) * 100) if total > 0 else 0
            })
    
    lang_stats = [l for l in lang_stats if l['total'] > 0]
    
    upcoming = WordProgress.objects.filter(
        user=user,
        mastered=False,
        next_review_date__gt=now
    ).select_related('word', 'word__language').order_by('next_review_date')[:5]
    
    recent_tests = CompletedTest.objects.filter(user=user).select_related('lesson')[:5]
    
    context = {
        'user': user,
        'total_words': total_words,
        'mastered_words': mastered_words,
        'due_for_review': due_for_review,
        'lang_stats': lang_stats,
        'upcoming': upcoming,
        'recent_tests': recent_tests,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def study(request):
    user = request.user
    lesson_id = request.GET.get('lesson')
    action = request.POST.get('action')
    
    all_lessons = Lesson.objects.filter(is_active=True).select_related('language')
    
    if not lesson_id:
        lessons_data = []
        for lesson in all_lessons:
            total = lesson.words.count()
            if total == 0:
                continue
            mastered = WordProgress.objects.filter(
                user=user,
                word__lesson=lesson,
                mastered=True
            ).count()
            percent = round((mastered / total) * 100) if total > 0 else 0
            
            is_completed = CompletedTest.objects.filter(user=user, lesson=lesson).exists()
            
            lessons_data.append({
                'lesson': lesson,
                'total': total,
                'mastered': mastered,
                'percent': percent,
                'is_completed': is_completed,
            })
        return render(request, 'core/study.html', {'lessons': lessons_data})
    
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    session_key = f'study_session_{user.id}_{lesson_id}'
    session_data = request.session.get(session_key, {})
    
    if action == 'start':
        words = list(Word.objects.filter(lesson=lesson).values_list('id', flat=True))
        if not words:
            messages.warning(request, 'В этом уроке нет слов. Добавьте слова в админ-панели.')
            return redirect('study')
        
        random.shuffle(words)
        
        request.session[session_key] = {
            'queue': words,
            'current_index': 0,
            'correct_count': 0,
            'wrong_count': 0,
            'answers': {},
            'completed': False,
        }
        request.session.modified = True
        return redirect(f"{reverse('study')}?lesson={lesson_id}")
    
    # core/views.py - исправленная часть (замените весь метод study или только часть с action='answer')

    if action == 'answer':
        word_id = request.POST.get('word_id')
        user_answer = request.POST.get('answer', '').strip().lower()
        
        if not word_id:
            messages.error(request, 'Ошибка: слово не найдено')
            return redirect(f"{reverse('study')}?lesson={lesson_id}")
        
        try:
            word = Word.objects.get(id=word_id)
            correct_answer = word.translation.lower()
            is_correct = user_answer == correct_answer
            
            progress, created = WordProgress.objects.get_or_create(
                user=user,
                word=word,
                defaults={'next_review_date': timezone.now()}
            )
            
            progress.record_answer(is_correct)
            
            session_data = request.session.get(session_key, {})
            current_index = session_data.get('current_index', 0)
            queue = session_data.get('queue', [])
            
            if 'answers' not in session_data:
                session_data['answers'] = {}
            session_data['answers'][word_id] = is_correct
            
            if is_correct:
                session_data['correct_count'] = session_data.get('correct_count', 0) + 1
                session_data['current_index'] = current_index + 1
            else:
                session_data['wrong_count'] = session_data.get('wrong_count', 0) + 1
                # ПРИ ОШИБКЕ: НЕ добавляем слово сразу в конец
                # Вместо этого перемещаем его на 3 позиции вперед или в конец с отступом
                # Это предотвратит немедленное повторное появление
                if word_id not in queue[current_index + 1:]:
                    # Вставляем слово на позицию current_index + 3 (или в конец, если мало слов)
                    new_position = min(current_index + 3, len(queue))
                    queue.pop(current_index)  # Удаляем текущее слово
                    queue.insert(new_position, int(word_id))  # Вставляем на новую позицию
                    session_data['queue'] = queue
                    # Не увеличиваем current_index, так как слово переместили
                else:
                    # Если слово уже есть в очереди, просто переходим дальше
                    session_data['current_index'] = current_index + 1
            
            request.session[session_key] = session_data
            request.session.modified = True
            
            # Проверяем, завершен ли урок (все слова пройдены правильно)
            # Урок завершен, когда все слова были отвечены правильно хотя бы раз
            all_answered_correctly = all(
                session_data['answers'].get(str(wid), False) for wid in queue
            )
            
            if session_data['current_index'] >= len(session_data.get('queue', [])) or all_answered_correctly:
                return redirect(f"{reverse('study')}?lesson={lesson_id}&completed=1")
            
        except Word.DoesNotExist:
            messages.error(request, 'Слово не найдено')
        
        return redirect(f"{reverse('study')}?lesson={lesson_id}")
    
    if action == 'complete':
        session_data = request.session.get(session_key, {})
        correct_count = session_data.get('correct_count', 0)
        wrong_count = session_data.get('wrong_count', 0)
        total = correct_count + wrong_count
        
        if total > 0:
            score_percent = int((correct_count / total) * 100)
            
            CompletedTest.objects.create(
                user=user,
                lesson=lesson,
                score_percent=score_percent,
                correct_count=correct_count,
                total_count=total
            )
            
            messages.success(request, f'Урок "{lesson.name}" пройден! Результат: {score_percent}%')
        
        if session_key in request.session:
            del request.session[session_key]
        
        return redirect('dashboard')
    
    total_words_in_lesson = lesson.words.count()
    if total_words_in_lesson == 0:
        return render(request, 'core/study.html', {
            'lesson': lesson,
            'no_words': True,
            'lessons': all_lessons
        })
    
    completed_flag = request.GET.get('completed')
    
    if not session_data or session_data.get('completed', False):
        return render(request, 'core/study.html', {
            'lesson': lesson,
            'total_words': total_words_in_lesson,
            'lessons': all_lessons,
            'show_start': True
        })
    
    if completed_flag:
        correct_count = session_data.get('correct_count', 0)
        wrong_count = session_data.get('wrong_count', 0)
        total = correct_count + wrong_count
        score_percent = int((correct_count / total) * 100) if total > 0 else 0
        
        return render(request, 'core/study.html', {
            'lesson': lesson,
            'completed': True,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'total_answered': total,
            'score_percent': score_percent,
            'total_words': total_words_in_lesson,
            'lessons': all_lessons
        })
    
    queue = session_data.get('queue', [])
    current_index = session_data.get('current_index', 0)
    
    if current_index >= len(queue):
        correct_count = session_data.get('correct_count', 0)
        wrong_count = session_data.get('wrong_count', 0)
        total = correct_count + wrong_count
        score_percent = int((correct_count / total) * 100) if total > 0 else 0
        
        return render(request, 'core/study.html', {
            'lesson': lesson,
            'completed': True,
            'correct_count': correct_count,
            'wrong_count': wrong_count,
            'total_answered': total,
            'score_percent': score_percent,
            'total_words': total_words_in_lesson,
            'lessons': all_lessons
        })
    
    current_word_id = queue[current_index]
    current_word = Word.objects.get(id=current_word_id)
    
    progress_percent = round((current_index / len(queue)) * 100) if queue else 0
    
    context = {
        'lesson': lesson,
        'current_word': current_word,
        'prompt_text': current_word.term,
        'answer_label': "Введите перевод на русском",
        'progress_percent': progress_percent,
        'current_index': current_index + 1,
        'total_in_session': len(queue),
        'correct_count': session_data.get('correct_count', 0),
        'wrong_count': session_data.get('wrong_count', 0),
        'lessons': all_lessons
    }
    return render(request, 'core/study.html', context)

@login_required
def vocabulary(request):
    user = request.user
    words = Word.objects.all().select_related('language', 'lesson').prefetch_related('categories', 'progress')
    
    lang_id = request.GET.get('lang')
    cat_id = request.GET.get('cat')
    level = request.GET.get('level')
    lesson_id = request.GET.get('lesson')
    
    if lang_id:
        words = words.filter(language_id=lang_id)
    if cat_id:
        words = words.filter(categories__id=cat_id)
    if lesson_id:
        words = words.filter(lesson_id=lesson_id)
    
    if level:
        if level == 'mastered':
            word_ids = WordProgress.objects.filter(user=user, mastered=True).values_list('word_id', flat=True)
            words = words.filter(id__in=word_ids)
        elif level == 'learning':
            word_ids = WordProgress.objects.filter(user=user, mastered=False, review_stage__gt=0).values_list('word_id', flat=True)
            words = words.filter(id__in=word_ids)
        elif level == 'new':
            word_ids = WordProgress.objects.filter(user=user, review_stage=0).values_list('word_id', flat=True)
            words = words.filter(id__in=word_ids)
        elif level == 'due':
            word_ids = WordProgress.objects.filter(
                user=user, 
                mastered=False, 
                next_review_date__lte=timezone.now()
            ).values_list('word_id', flat=True)
            words = words.filter(id__in=word_ids)
    
    words_list = []
    for word in words:
        progress = WordProgress.objects.filter(user=user, word=word).first()
        words_list.append({
            'word': word,
            'progress': progress,
            'stage_name': progress.get_stage_name() if progress else 'Новое',
            'needs_review': progress.needs_review() if progress and not progress.mastered else False,
        })
    
    languages = Language.objects.all()
    categories = Category.objects.all()
    lessons = Lesson.objects.filter(is_active=True)
    
    context = {
        'words': words_list,
        'languages': languages,
        'categories': categories,
        'lessons': lessons,
        'selected_lang': lang_id,
        'selected_cat': cat_id,
        'selected_level': level,
        'selected_lesson': lesson_id,
    }
    return render(request, 'core/vocabulary.html', context)

@login_required
def profile(request):
    user = request.user
    
    total_progress = WordProgress.objects.filter(user=user)
    stats = {
        'total': total_progress.count(),
        'mastered': total_progress.filter(mastered=True).count(),
        'learning': total_progress.filter(mastered=False, review_stage__gt=0).count(),
        'new': total_progress.filter(review_stage=0).count(),
    }
    
    history = total_progress.filter(last_answered__isnull=False).select_related('word', 'word__language').order_by('-last_answered')[:20]
    
    completed_tests = CompletedTest.objects.filter(user=user).select_related('lesson')[:10]
    
    from django.db.models import Avg
    avg_score = CompletedTest.objects.filter(user=user).aggregate(avg=Avg('score_percent'))['avg']
    
    context = {
        'user': user,
        'stats': stats,
        'history': history,
        'completed_tests': completed_tests,
        'avg_score': round(avg_score) if avg_score else 0,
    }
    return render(request, 'core/profile.html', context)

@login_required
def completed_tests(request):
    user = request.user
    tests = CompletedTest.objects.filter(user=user).select_related('lesson', 'lesson__language').order_by('-completed_at')
    
    from django.db.models import Avg, Max
    total_tests = tests.count()
    avg_score = tests.aggregate(avg=Avg('score_percent'))['avg']
    best_score = tests.aggregate(best=Max('score_percent'))['best']
    
    context = {
        'tests': tests,
        'total_tests': total_tests,
        'avg_score': round(avg_score) if avg_score else 0,
        'best_score': best_score if best_score else 0,
    }
    return render(request, 'core/completed_tests.html', context)

@login_required
def repeat_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    
    words = Word.objects.filter(lesson=lesson)
    for word in words:
        progress, created = WordProgress.objects.get_or_create(user=request.user, word=word)
        progress.next_review_date = timezone.now()
        progress.save()
    
    messages.success(request, f'Начинаем повторение урока "{lesson.name}"')
    return redirect(f"{reverse('study')}?lesson={lesson_id}")

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Неверный логин или пароль')
    return render(request, 'core/login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь уже существует')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect('dashboard')
    return render(request, 'core/register.html')

def logout_view(request):
    logout(request)
    return redirect('login')