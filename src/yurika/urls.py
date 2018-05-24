from django.conf.urls import include, url
from django.contrib import admin


urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(r'^', include('yurika.accounts.auth.urls')),
    url(r'^api/auth/', include('rest_framework.urls')),
    url(r'^api/', include('yurika.api.urls')),
    url(r'^', include('yurika.bricks.urls')),
]
