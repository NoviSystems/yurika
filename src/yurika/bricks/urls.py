from django.conf.urls import url

from . import views


urlpatterns = [
    # A view named "home" is referenced in a few places.
    # Make sure to update the references if you change or delete this url line!
    url(r'^$', views.HomeView.as_view(), name='home'),
]
