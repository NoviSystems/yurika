from django.conf.urls import url

from . import views

urlpatterns = [
    # A view named "home" is referenced in a few places.
    # Make sure to update the references if you change or delete this url line!
    url(r"^projects/$", views.project_list, name="project-list"),
    url(r"^projects/(?P<slug>[-\w]+)/$", views.project_detail, name="project-detail"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/$", views.tree_detail, name="tree-detail"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/insert/(?P<id>[\d]+)/$", views.tree_insert, name="tree-insert-at"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/insert/$", views.tree_insert, name="tree-insert"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/edit/(?P<id>[\d]+)/$", views.tree_edit, name="tree-edit-at"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/edit/$", views.tree_edit, name="tree-edit"),
    url(r"^api/trees/(?P<slug>[-\w]+)/$", views.tree_json, name="tree-json"),
    url(r"^$", views.home, name="home"),
]
