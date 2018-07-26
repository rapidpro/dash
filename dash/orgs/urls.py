

from . import views

urlpatterns = views.OrgCRUDL().as_urlpatterns()
urlpatterns += views.OrgBackgroundCRUDL().as_urlpatterns()
urlpatterns += views.TaskCRUDL().as_urlpatterns()
urlpatterns += views.OrgBackendCRUDL().as_urlpatterns()
