# core/models.py - исправленная версия (lesson может быть пустым)

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

class Language(models.Model):
    code = models.CharField(max_length=5, unique=True, verbose_name="Код языка")
    name = models.CharField(max_length=100, verbose_name="Название языка")
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        verbose_name = "Язык"
        verbose_name_plural = "Языки"

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

class Lesson(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название урока")
    description = models.TextField(blank=True, verbose_name="Описание")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='lessons', verbose_name="Язык")
    order = models.IntegerField(default=0, verbose_name="Порядок урока")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    def __str__(self):
        return f"{self.language.name} — {self.name}"
    
    class Meta:
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
        ordering = ['language', 'order']
    
    def get_word_count(self):
        return self.words.count()
    
    def get_user_progress(self, user):
        if not user.is_authenticated:
            return {'total': 0, 'mastered': 0, 'percent': 0}
        
        total = self.words.count()
        if total == 0:
            return {'total': 0, 'mastered': 0, 'percent': 0}
        
        mastered = WordProgress.objects.filter(
            user=user,
            word__lesson=self,
            mastered=True
        ).count()
        
        return {
            'total': total,
            'mastered': mastered,
            'percent': round((mastered / total) * 100) if total > 0 else 0
        }

class Word(models.Model):
    term = models.CharField(max_length=255, verbose_name="Иностранное слово")
    translation = models.CharField(max_length=255, verbose_name="Перевод")
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='words', verbose_name="Язык")
    categories = models.ManyToManyField(Category, related_name='words', verbose_name="Категории", blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='words', verbose_name="Урок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    
    def __str__(self):
        return f"{self.term} → {self.translation}"
    
    class Meta:
        verbose_name = "Слово"
        verbose_name_plural = "Слова"
        ordering = ['lesson__order', 'term']

class WordProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='word_progress')
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='progress')
    mastered = models.BooleanField(default=False, verbose_name="Слово изучено")
    correct_count = models.IntegerField(default=0, verbose_name="Правильных ответов")
    wrong_count = models.IntegerField(default=0, verbose_name="Неправильных ответов")
    last_answered = models.DateTimeField(null=True, blank=True, verbose_name="Последний ответ")
    next_review_date = models.DateTimeField(default=timezone.now, verbose_name="Следующее повторение")
    review_interval_days = models.IntegerField(default=1, verbose_name="Интервал повторения (дней)")
    review_stage = models.IntegerField(default=0, verbose_name="Стадия повторения (0-5)")
    
    class Meta:
        verbose_name = "Прогресс слова"
        verbose_name_plural = "Прогресс слов"
        unique_together = ('user', 'word')
    
    def record_answer(self, is_correct):
        self.last_answered = timezone.now()
        
        if is_correct:
            self.correct_count += 1
            
            if self.review_stage == 0 and self.correct_count >= 1:
                self.review_stage = 1
                self.review_interval_days = 1
            elif self.review_stage == 1 and self.correct_count >= 2:
                self.review_stage = 2
                self.review_interval_days = 3
            elif self.review_stage == 2 and self.correct_count >= 3:
                self.review_stage = 3
                self.review_interval_days = 7
            elif self.review_stage == 3 and self.correct_count >= 4:
                self.review_stage = 4
                self.review_interval_days = 14
            elif self.review_stage == 4 and self.correct_count >= 5:
                self.review_stage = 5
                self.review_interval_days = 30
                self.mastered = True
            
            if self.correct_count >= 5 and not self.mastered:
                self.mastered = True
                self.review_stage = 5
                self.review_interval_days = 30
        else:
            self.wrong_count += 1
            self.correct_count = 0
            if self.review_stage > 0:
                self.review_stage -= 1
                intervals = {0: 0, 1: 1, 2: 3, 3: 7, 4: 14, 5: 30}
                self.review_interval_days = intervals.get(self.review_stage, 1)
            self.mastered = False
        
        self.next_review_date = timezone.now() + datetime.timedelta(days=self.review_interval_days)
        self.save()
    
    def get_stage_name(self):
        stages = {
            0: 'Новое',
            1: 'Начало',
            2: 'В процессе',
            3: 'Укрепление',
            4: 'Закрепление',
            5: 'Мастер'
        }
        return stages.get(self.review_stage, 'Новое')
    
    def needs_review(self):
        return timezone.now() >= self.next_review_date and not self.mastered

class CompletedTest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='completed_tests')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='completed_tests')
    score_percent = models.IntegerField(verbose_name="Результат (%)")
    correct_count = models.IntegerField(verbose_name="Правильных ответов")
    total_count = models.IntegerField(verbose_name="Всего слов")
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата прохождения")
    
    class Meta:
        verbose_name = "Пройденный тест"
        verbose_name_plural = "Пройденные тесты"
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.name} - {self.score_percent}%"