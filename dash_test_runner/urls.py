from __future__ import unicode_literals

from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^/', include('dash_test_runner.testapp.urls')),

    url(r'^manage/', include('dash.orgs.urls')),
    url(r'^manage/', include('dash.stories.urls')),
    url(r'^manage/', include('dash.dashblocks.urls')),
    url(r'^manage/', include('dash.categories.urls')),
    url(r'^users/', include('dash.users.urls')),
    url(r'^admin/', include(admin.site.urls)),
]
