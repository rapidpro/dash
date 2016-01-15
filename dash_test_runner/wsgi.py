from __future__ import unicode_literals

"""
WSGI config for dash_test_runner project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dash_test_runner.settings")

from django.core.wsgi import get_wsgi_application  # noqa
application = get_wsgi_application()
