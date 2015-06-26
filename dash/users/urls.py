from smartmin.users.views import login

from django.conf import settings
from django.conf.urls import url
from django.contrib.auth.views import logout

from . import views


logout_url = getattr(settings, 'LOGOUT_REDIRECT_URL', None)

urlpatterns = [
    url(r'^login/$',
        login,
        dict(template_name='smartmin/users/login.html'),
        name="users.user_login"),
    url(r'^logout/$',
        logout,
        dict(redirect_field_name='go', next_page=logout_url),
        name="users.user_logout"),
]

urlpatterns += views.UserCRUDL().as_urlpatterns()
