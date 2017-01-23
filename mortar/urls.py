from django.conf.urls import url

from . import views

urlpatterns = [
    # A view named "home" is referenced in a few places.
    # Make sure to update the references if you change or delete this url line!
    url(r"^projects/$", views.project_list, name="project-list"),
    url(r"^projects/(?P<slug>[-\w]+)/$", views.project_detail, name="project-detail"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/$", views.tree_detail, name="tree-detail"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/insert/(?P<id>[\d]+)/$", views.cat_insert, name="cat-insert-at"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/insert/$", views.cat_insert, name="cat-insert"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/edit/(?P<id>[\d]+)/$", views.cat_edit, name="cat-edit-at"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/edit/$", views.cat_edit, name="cat-edit"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/branch/(?P<id>[\d]+)/$", views.tree_branch, name="tree-branch-new"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/branch/$", views.tree_branch, name="tree-branch"),
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/edit-name/$", views.tree_edit, name="tree-edit"),
    url(r"^api/trees/(?P<slug>[-\w]+)/$", views.tree_json, name="tree-json"),
    url(r"^api/trees/(?P<slug>[-\w]+)/rules/$", views.tree_rules, name="tree-rules"),
    url(r"^$", views.home, name="home"),
]
