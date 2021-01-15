import os

from django.conf import settings  # noqa

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_test_runner.settings')


app = Celery('dash_test_runner')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
