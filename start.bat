@echo off
echo Запуск DictionaryPro...
echo Установка зависимостей...
pip install django
echo Запуск сервера...
start python manage.py runserver
timeout /t 3
start http://127.0.0.1:8000
echo Приложение запущено!
pause