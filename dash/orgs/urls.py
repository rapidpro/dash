from __future__ import unicode_literals

from . import views


urlpatterns = views.OrgCRUDL().as_urlpatterns()
urlpatterns += views.OrgBackgroundCRUDL().as_urlpatterns()
urlpatterns += views.TaskCRUDL().as_urlpatterns()
