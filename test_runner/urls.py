from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r"^/", include("test_runner.testapp.urls")),
    url(r"^manage/", include("dash.orgs.urls")),
    url(r"^manage/", include("dash.stories.urls")),
    url(r"^manage/", include("dash.dashblocks.urls")),
    url(r"^manage/", include("dash.categories.urls")),
    url(r"^manage/", include("dash.tags.urls")),
    url(r"^users/", include("dash.users.urls")),
    url(r"^admin/", admin.site.urls),
]
