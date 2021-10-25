import os

from django.conf import settings  # noqa

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_runner.settings")


app = Celery("test_runner")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
