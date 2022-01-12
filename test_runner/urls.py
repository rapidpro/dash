from django.conf.urls import include
from django.contrib import admin
from django.urls import re_path

urlpatterns = [
    re_path(r"^/", include("test_runner.testapp.urls")),
    re_path(r"^manage/", include("dash.orgs.urls")),
    re_path(r"^manage/", include("dash.stories.urls")),
    re_path(r"^manage/", include("dash.dashblocks.urls")),
    re_path(r"^manage/", include("dash.categories.urls")),
    re_path(r"^manage/", include("dash.tags.urls")),
    re_path(r"^users/", include("dash.users.urls")),
    re_path(r"^admin/", admin.site.urls),
]
