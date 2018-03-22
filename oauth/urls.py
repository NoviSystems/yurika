from django.conf.urls import url

from . import views


urlpatterns = [
    url(r"^provider/(?P<provider>[a-z]+)/login$", views.login,
        name="oauth_login"),
    url(r"^provider/(?P<provider>[a-z]+)/complete$", views.complete,
        name="oauth_complete"),
    url(r"^associate$", views.associate, name="oauth_associate"),
]
