v1.14.1 (2023-10-05)
-------------------------
 * Merge pull request #172 from rapidpro/dependabot/pip/pillow-10.0.1
 * Merge pull request #171 from rapidpro/dependabot/pip/urllib3-2.0.6
 * Bump pillow from 9.5.0 to 10.0.1
 * Bump urllib3 from 2.0.4 to 2.0.6

v1.14.0 (2023-08-22)
-------------------------
 * Merge pull request #170 from rapidpro/convert_templates
 * lint templates
 * Use latest djlint
 * Convert testapp haml template
 * Remove django-hamlpy
 * Convert haml templates
 * Update deps, add djlint

v1.13.0 (2023-07-06)
-------------------------
 * Upgrade to psycopg non-binary
 * Bump django from 4.2.1 to 4.2.3

v1.12.0 (2023-05-10)
-------------------------
 * Merge pull request #164 from rapidpro/update-client
 * Update rapidpro-python
 * Merge pull request #162 from rapidpro/dependabot/pip/sqlparse-0.4.4
 * Merge pull request #163 from rapidpro/dependabot/pip/django-4.1.9
 * Bump django from 4.1.7 to 4.1.9
 * Bump sqlparse from 0.4.3 to 0.4.4

v1.11.1 (2023-04-19)
-------------------------
 * Merge pull request #161 from rapidpro/update-coverage-deps
 * Replace codecov with coverage
 * Merge pull request #160 from rapidpro/more-index-optimizations
 * More stories query optimization
 * Merge pull request #159 from rapidpro/dependabot/pip/redis-4.5.4
 * Bump redis from 4.5.3 to 4.5.4
 * Add indexes to optimize more the page loading
 * Merge pull request #158 from rapidpro/dependabot/pip/redis-4.5.3
 * Bump redis from 4.5.1 to 4.5.3

v1.11.0 (2023-03-07)
-------------------------
 * Update to latest rapidpro client
 * Update hamlpy

v1.10.5 (2023-02-27)
-------------------------
 * Merge pull request #156 from rapidpro/fix-stories-links
 * Fix story audio link formatting

v1.10.4 (2023-02-22)
-------------------------
 * Replace inspect removed method

v1.10.3 (2023-02-20)
-------------------------
 * Merge pull request #153 from rapidpro/dependabot/pip/django-4.1.7
 * Merge pull request #154 from rapidpro/fix-ga-deps
 * Fix github action deps
 * Bump django from 4.1.6 to 4.1.7
 * Merge pull request #152 from rapidpro/dependabot/pip/django-4.1.6
 * Bump django from 4.1.5 to 4.1.6

v1.10.2 (2023-01-24)
-------------------------
 * Merge pull request #151 from rapidpro/fix-compressor
 * Update deps
 * Update django compressor

v1.10.1 (2023-01-24)
-------------------------
 * Merge pull request #150 from rapidpro/updates-django
 * Update django and celery

v1.10.0 (2023-01-23)
-------------------------
 * Make python version for release 3.10
 * Merge pull request #149 from rapidpro/updates
 * Update to latest smartmin
 * Fix redis install action version
 * Update CI versions
 * Merge pull request #148 from rapidpro/updates
 * Update to match rapipro-python updates
 * Update black
 * Update config and deps
 * update code_checks
 * Switch from flake8 to ruff
 * Move isort config into pyproject.toml
 * Move coverage config into pyproject.toml
 * Merge pull request #145 from rapidpro/dependabot/pip/pillow-9.3.0
 * Merge pull request #146 from rapidpro/dependabot/pip/certifi-2022.12.7
 * Merge pull request #147 from rapidpro/dependabot/pip/django-4.0.8
 * Merge branch 'main' into dependabot/pip/pillow-9.3.0
 * Bump django from 4.0.7 to 4.0.8
 * Merge branch 'main' into dependabot/pip/certifi-2022.12.7
 * Merge pull request #144 from rapidpro/dependabot/pip/django-4.0.7
 * Bump certifi from 2021.10.8 to 2022.12.7
 * Bump pillow from 9.0.1 to 9.3.0
 * Bump django from 4.0.6 to 4.0.7
 * Merge pull request #143 from rapidpro/dependabot/pip/django-4.0.6
 * Bump django from 4.0.4 to 4.0.6
 * Merge pull request #142 from rapidpro/dependabot/pip/django-4.0.4
 * Bump django from 4.0.2 to 4.0.4

v1.9.3
----------
 * Merge pull request #141 from rapidpro/optimize-queries
 * Remove unnecessary if block
 * Remove unnecessary codes
 * Add prefetch dashblocks when loading dashblocks
 * Reduce DB queries
 * Merge pull request #140 from rapidpro/dependabot/pip/pillow-9.0.1
 * Bump pillow from 9.0.0 to 9.0.1
 * Merge pull request #139 from rapidpro/dependabot/pip/django-4.0.2
 * Bump django from 4.0.1 to 4.0.2

v1.9.2
----------
 * Update to latest pillow, smartmin

v1.9.1
----------
 * Add missing migrations

v1.9.0
----------
 * Add support for Django 4

v1.8.3
----------
 * Merge pull request #133 from rapidpro/fix-dashblock_views
 * pin black
 * Update code checks
 * Fix dashblock views

v1.8.2
----------
 * Merge pull request #132 from rapidpro/report-attachments
 * Show has report stories
 * Add attachment field to story to upload PDF reports

v1.8.1
----------
 * Merge pull request #129 from rapidpro/images-names-conflicting
 * Merge pull request #131 from rapidpro/fix-dashblocks-link-label
 * Run code_checks
 * Add migrations
 * Fix conflicts
 * Fix confusing label for the link slug on the dashblock forms
 * Keep filename first 36 characters in the new filename
 * Generate a random name for images when uploading them

v1.8.0
----------
 * Update to latest celery 5.x and test on Python 3.9.x

v1.7.4
----------
 * Add missing migration

v1.7.3
----------
 * Update Org.config to newer JSONField to remove deprecaction warning

v1.7.2
----------
 * Merge pull request #126 from rapidpro/add-tags
 * Address PR comments
 * Few tweaks for ordering
 * Add delete tag view
 * Remove org name on tags str representation
 * Adjust black dep specification
 * Use the request org in the context for tags views
 * Tweak asserts
 * Add tags app
 * Merge pull request #127 from rapidpro/blackify
 * blackify

v1.7.1
----------
 * Allow a way to customize the creation and update of the local instance, defaults to the current behavior

v1.7.0
----------
 * Add support for Django 3.2 LTS

v1.6.1
----------
 * Update rapidpro-python

v1.6.0
----------
 * Add support for partial syncs in sync_local_to_changes

v1.5.7
----------
 * Allow previous results to be passed to org tasks

v1.5.6
----------
 * Update to latest smartmin

v1.5.5
----------
 * Update to latest smartmin

v1.5.4
----------
 * Rework dependencies to support older redis

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
