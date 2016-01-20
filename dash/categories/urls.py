from __future__ import unicode_literals

from . import views


urlpatterns = views.CategoryCRUDL().as_urlpatterns()
urlpatterns += views.CategoryImageCRUDL().as_urlpatterns()
