from .views import *

urlpatterns = DashBlockTypeCRUDL().as_urlpatterns()
urlpatterns += DashBlockCRUDL().as_urlpatterns()
urlpatterns += DashBlockImageCRUDL().as_urlpatterns()

