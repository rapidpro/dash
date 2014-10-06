from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'dash_test_runner.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^manage/', include('dash.orgs.urls')),
    url(r'^manage/', include('dash.stories.urls')),
    url(r'^manage/', include('dash.dashblocks.urls')),
    url(r'^manage/', include('dash.categories.urls')),
    url(r'^users/', include('dash.users.urls')),

    url(r'^admin/', include(admin.site.urls)),
)
