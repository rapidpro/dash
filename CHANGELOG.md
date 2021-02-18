v1.5.3
----------
 * Add some extra functionality to MockResponse

v1.5.2
----------
 * Merge pull request #119 from rapidpro/move-mock-response
 * Move MockResponse to dash.test to allow reuse

v1.5.1
----------
 * Task list shouldn't include inactive orgs
 * Bump CI testin to PG 11 and 12

v1.5.0
----------
 * Convert to poetry

1.4.6 (2020-07-09)
=================
 * Explicitly log failing org task to sentry

1.4.5 (2019-02-06)
=================
 * Explicitly log failing org task to sentry

1.4.4 (2019-02-01)
=================
 * Remove f-strings as we still test on python 3.5

1.4.3 (2019-01-11)
=================
 * Update summernote WYSIWYG library

1.4.2 (2019-01-11)
=================
 * Updates to support Django 2.1
 * Drop support for django 1.11

1.4.1 (2019-01-09)
=================
 * Upgrade to latest smartmin

1.4 (2018-08-14)
=================
 * Supports Python 3 only
 * Support Django 1.11 and 2.0
 * Code format tools (isort, black)

1.3.7 (2018-05-28)
=================
 * Include static folder in release

1.3.6 (2018-05-28)
=================
 * Switch Text editor to Summernote JS library

1.3.4 (2018-04-27)
=================
 * Add migrations to clean up org config
 
1.3.3 (2018-04-26)
=================
 * Make filtering by backend field on model optional

1.3.2 (2018-04-06)
==================
 * Use . paths on the Org config to set and retrieve the values
 * Use a foreign key for the backend fields and use OrgBackend object instead of slug as arguments

1.3.1 (2018-03-22)
==================
 * Add OrgBackend model to store the configurations for backends
 * Remove `api_token` key from Org config
 * Add DATA_API_BACKEND_TYPES settings for backend types

1.3 (2018-03-15)
==================
 * Remove Org api_token field
 * Convert Org config field to JSONField
 * Support multiple backend configurations
 * Add DATA_API_BACKENDS_CONFIG settings
 * Add BACKENDS_ORG_CONFIG_FIELDS settings
 * Migrations to move existing backend API specific under rapidpro config

1.2.7 (2018-03-08)
==================
 * Fix migrations

1.2.6 (2018-03-08)
==================
 * Fix migrations

1.2.5 (2018-03-08)
==================
 * Restructure org config dict

1.2.4 (2018-01-09)
==================
 * Fix derive fields to include read only fields

1.2.3 (2018-01-09)
==================
 * Add way to display read only org config fields to admins

1.2.2 (2017-12-04)
==================
 * Improve chunks util method so that it doesn't load the entire source iterator into a list
 
1.2.1 (2017-06-15)
==================
 * Support Django 1.10 new middleware style

1.2 (2017-06-07)
==================
 * Update to latest smartmin which adds support for Django 1.11 and Python 3.6

1.1.1 (2017-03-01)
==================
 * Update to latest smartmin which replaces uses of auto_now/auto_now_add in models with overridable defaults

1.1 (2016-12-15)
==================
 * Added support for Django 1.10 https://github.com/rapidpro/dash/pull/90
 * Dropped support for Django 1.8

1.0.4 (2016-12-09)
==================
 * Updated to latest django-hamlpy 1.x https://github.com/rapidpro/dash/pull/89
 
1.0.3 (2016-11-11)
==================
 * Added support for configurable timeouts on org tasks https://github.com/rapidpro/dash/pull/88
 
1.0.2 (2016-10-31)
==================
 * Switched org.timzeone to be an actual timezone field

1.0.1 (2016-10-26)
==================
 * Added support for Django 1.9
 * Improved support for Python 3
