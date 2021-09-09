import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
from mspark_whatsapp_analyzer import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mspark_whatsapp_analyzer.settings')

app = Celery('mspark_whatsapp_analyzer')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
app.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))