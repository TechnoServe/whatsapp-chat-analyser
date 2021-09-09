web: gunicorn mspark_whatsapp_analyzer.wsgi --log-file -
release:  python manage.py migrate
worker: celery -A mspark_whatsapp_analyzer worker -l info
beat: celery -A mspark_whatsapp_analyzer beat -l info