from __future__ import unicode_literals

from . import views


urlpatterns = views.DashBlockTypeCRUDL().as_urlpatterns()
urlpatterns += views.DashBlockCRUDL().as_urlpatterns()
urlpatterns += views.DashBlockImageCRUDL().as_urlpatterns()
