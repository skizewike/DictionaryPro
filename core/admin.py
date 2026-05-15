from django.contrib import admin
from .models import Language, Category, Lesson, Word, WordProgress, CompletedTest

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('name', 'language', 'order', 'is_active')
    list_filter = ('language', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('language', 'order')

@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ('term', 'translation', 'language', 'lesson', 'created_at')
    list_filter = ('language', 'categories', 'lesson', 'created_at')
    search_fields = ('term', 'translation')
    filter_horizontal = ('categories',)
    ordering = ('lesson__order', 'term')

@admin.register(WordProgress)
class WordProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'word', 'mastered', 'review_stage', 'next_review_date')
    list_filter = ('mastered', 'review_stage')
    search_fields = ('user__username', 'word__term')
    readonly_fields = ('correct_count', 'wrong_count', 'last_answered')

@admin.register(CompletedTest)
class CompletedTestAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'score_percent', 'completed_at')
    list_filter = ('lesson', 'completed_at')
    search_fields = ('user__username', 'lesson__name')
    readonly_fields = ('score_percent', 'correct_count', 'total_count')

admin.site.site_header = "DictionaryPro Administration"
admin.site.site_title = "DictionaryPro Admin"
admin.site.index_title = "Управление приложением"