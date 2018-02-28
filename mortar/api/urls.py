from rest_framework import routers

from . import views


router = routers.DefaultRouter()
router.register('queries', views.QueryViewSet)

urlpatterns = router.urls
