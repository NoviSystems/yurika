from django.conf.urls import url, include

from . import views

urlpatterns = [
    # A view named "home" is referenced in a few places.
    # Make sure to update the references if you change or delete this url line!
    url(r"^explorer/", include("explorer.urls")),
    url(r"", views.home, name="portrait"),
]
