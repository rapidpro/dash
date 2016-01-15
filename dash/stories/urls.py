from __future__ import unicode_literals

from . import views


urlpatterns = views.StoryCRUDL().as_urlpatterns()
