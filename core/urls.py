# core/urls.py (ПОЛНОСТЬЮ ПЕРЕПИСАН)
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('study/', views.study, name='study'),
    path('vocabulary/', views.vocabulary, name='vocabulary'),
    path('profile/', views.profile, name='profile'),
    path('completed-tests/', views.completed_tests, name='completed_tests'),
    path('repeat-lesson/<int:lesson_id>/', views.repeat_lesson, name='repeat_lesson'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]