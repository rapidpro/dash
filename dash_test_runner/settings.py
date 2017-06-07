from __future__ import unicode_literals

"""
Django settings for dash_test_runner project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import logging
import os
import warnings

from django.utils.translation import ugettext_lazy as _

logging.disable(logging.WARN)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = '*z(s8sb^&p-6n#b!w=1-d2bho*+*0g_51bnx=-@a$wj6dnpd2w'

DEBUG = True

ALLOWED_HOSTS = ['testserver', '.ureport.io']

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'compressor',
    'sorl.thumbnail',
    'timezone_field',

    'smartmin',
    'smartmin.users',

    'dash.orgs',
    'dash.categories',
    'dash.dashblocks',
    'dash.stories',
    'dash.utils',

    'dash_test_runner.testapp'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'smartmin.users.middleware.ChangePasswordMiddleware',
    'smartmin.middleware.TimezoneMiddleware',
    'dash.orgs.middleware.SetOrgMiddleware',
)

warnings.filterwarnings('error', r"DateTimeField received a naive datetime",
                        RuntimeWarning, r'django\.db\.models\.fields')

ROOT_URLCONF = 'dash_test_runner.urls'

WSGI_APPLICATION = 'dash_test_runner.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


SITE_ID = 1
LANGUAGE_CODE = 'en-us'
LANGUAGES = (('en', "English"), ('fr', "French"))
DEFAULT_LANGUAGE = "en"
TIME_ZONE = 'UTC'
USER_TIME_ZONE = 'Africa/Kigali'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
)

# create the smartmin CRUDL permissions on all objects
PERMISSIONS = {
    '*': ('create',  # can create an object
          'read',   # can read an object, viewing it's details
          'update',  # can update an object
          'delete',  # can delete an object,
          'list'),  # can view a list of the objects
    'auth.user': ('profile', 'forget', 'recover', 'expired', 'failed', 'newpassword', 'mimic'),
    'orgs.org': ('choose', 'home', 'edit', 'manage_accounts', 'create_login', 'join'),
    'stories.story': ('images',),
}

# assigns the permissions that each group should have, here creating an Administrator group with
# authority to create and change users
GROUP_PERMISSIONS = {
    "Administrators": (
        'categories.category.*',
        'categories.categoryimage.*',
        'dashblocks.dashblock.*',
        'users.user_profile',
        'orgs.org_home',
        'orgs.org_edit',
        'orgs.org_manage_accounts',
        'orgs.orgbackground.*',
        'stories.story.*',
    ),
    "Editors": (
        'categories.category.*',
        'categories.categoryimage.*',
        'dashblocks.dashblock.*',
        'dashblocks.dashblocktype.*',
        'news.newsitem.*',
        'news.video.*',
        'orgs.org_home',
        'orgs.org_profile',
        'polls.poll.*',
        'polls.pollcategory.*',
        'polls.pollimage.*',
        'polls.featuredresponse.*',
        'stories.story.*',
        'stories.storyimage.*',
        'users.user_profile',
    ),
    "Viewers": [],
}

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = "/manage/org/choose/"
LOGOUT_REDIRECT_URL = "/"

# ----------------------------------------------------------------------------
# Async tasks with django-celery
# ----------------------------------------------------------------------------

CELERY_RESULT_BACKEND = None

BROKER_BACKEND = 'redis'
BROKER_HOST = 'localhost'
BROKER_PORT = 6379
BROKER_VHOST = '4'

# RapidPRO
SITE_API_HOST = 'http://localhost:8001'
HOSTNAME = 'ureport.io'
SITE_CHOOSER_TEMPLATE = 'orgs/org_chooser.html'
SITE_CHOOSER_URL_NAME = 'orgs.org_chooser'
SITE_ALLOW_NO_ORG = ('orgs.task_list', 'testapp.contact_test_tags')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/10',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

ORG_CONFIG_FIELDS = [
    dict(name='shortcode',
         field=dict(help_text=_("The shortcode that users will use to contact U-report locally"),
                    required=True)),
    dict(name='join_text',
         field=dict(help_text=_("The short text used to direct visitors to join U-report"),
                    required=False)),
    dict(name='join_fg_color',
         field=dict(help_text=_("The color used to draw the text on the join bar"),
                    required=False),
         superuser_only=True),
    dict(name='join_bg_color',
         field=dict(help_text=_("The color used to draw the background on the join bar"),
                    required=False),
         superuser_only=True),
    dict(name='primary_color',
         field=dict(help_text=_("The primary color for styling for this organization"),
                    required=False),
         superuser_only=True),
    dict(name='secondary_color',
         field=dict(help_text=_("The secondary color for styling for this organization"),
                    required=False),
         superuser_only=True),
    dict(name='bg_color',
         field=dict(help_text=_("The background color for the site"),
                    required=False),
         superuser_only=True),
    dict(name='colors',
         field=dict(help_text=_("Up to 6 colors for styling charts, use comma between colors"),
                    required=False),
         superuser_only=True),
    dict(name='google_tracking_id',
         field=dict(help_text=_("The Google Analytics Tracking ID for this organization"),
                    required=False)),
    dict(name='youtube_channel_url',
         field=dict(help_text=_("The URL to the Youtube channel for this organization"),
                    required=False)),
    dict(name='facebook_page_url',
         field=dict(help_text=_("The URL to the Facebook page for this organization"),
                    required=False)),
    dict(name='twitter_handle',
         field=dict(help_text=_("The Twitter handle for this organization"),
                    required=False)),
    dict(name='twitter_user_widget',
         field=dict(help_text=_("The Twitter widget used for following new users"),
                    required=False)),
    dict(name='twitter_search_widget',
         field=dict(help_text=_("The Twitter widget used for searching"),
                    required=False)),
    dict(name='reporter_group',
         field=dict(help_text=_("The name of txbhe Contact Group that contains "
                                "registered reporters")),
         superuser_only=True),
    dict(name='born_label',
         field=dict(help_text=_("The label of the Contact Field that contains "
                                "the birth date of reporters")),
         superuser_only=True),
    dict(name='gender_label',
         field=dict(help_text=_("The label of the Contact Field that contains "
                                "the gender of reporters")),
         superuser_only=True),
    dict(name='occupation_label',
         field=dict(help_text=_("The label of the Contact Field that contains "
                                "the occupation of reporters")),
         superuser_only=True),
    dict(name='registration_label',
         field=dict(help_text=_("The label of the Contact Field that contains "
                                "the registration date of reporters")),
         superuser_only=True),
    dict(name='state_label',
         field=dict(help_text=_("The label of the Contact Field that contains "
                                "the State of reporters")),
         superuser_only=True),
    dict(name='district_label',
         field=dict(help_text=_("The label of the Contact Field that contains "
                                "the District of reporters")),
         superuser_only=True),
    dict(name='male_label',
         field=dict(help_text=_("The label assigned to U-reporters that are Male.")),
         superuser_only=True),
    dict(name='female_label',
         field=dict(help_text=_("The label assigned to U-reporters that are Female.")),
         superuser_only=True),
    dict(name='has_jobs',
         field=dict(help_text=_("If there are jobs to be shown on the public site"),
                    required=False)),
    # dict(name='featured_state',
    #      field=dict(help_text=_("Choose the featured State of reporters "
    #                             "shown on the home page"))),
]

# ----------------------------------------------------------------------------
# Directory Configuration
# ----------------------------------------------------------------------------

PROJECT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)))
RESOURCES_DIR = os.path.join(PROJECT_DIR, '../resources')
TESTFILES_DIR = os.path.join(PROJECT_DIR, '../testfiles')
MEDIA_ROOT = os.path.join(PROJECT_DIR, '../media')
MEDIA_URL = "/media/"

# ----------------------------------------------------------------------------
# Templates Configuration
# ----------------------------------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_DIR, '../templates')],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'dash.orgs.context_processors.user_group_perms_processor',
                'dash.orgs.context_processors.set_org_processor',
            ],
            'loaders': [
                'dash.utils.haml.HamlFilesystemLoader',
                'dash.utils.haml.HamlAppDirectoriesLoader',
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'debug': DEBUG
        },
    },
]
