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
    url(r"^projects/(?P<project_slug>[-\w]+)/(?P<slug>[-\w]+)/query/$", views.tree_query, name="tree-query"),
    url(r"^annotations/(?P<slug>[-\w]+)/$", views.annotation_list, name="annotation-list"),
    url(r"^annotations/(?P<slug>[-\w]+)/query/$", views.annotation_query, name="annotation-query"),
    url(r"^annotations/terms/(?P<pk>\d+)/$", views.term_vectors, name="term-vectors"),
    url(r"^query/(?P<slug>[-\w]+)/create/$", views.query_part, name="query-part"),
    url(r"^dictionaries/$", views.dictionary_list, name='dictionary-list'),
    url(r"^dictionaries/(?P<pk>\d+)/$", views.dictionary_detail, name="dictionary-detail"),
    url(r"^api/trees/(?P<slug>[-\w]+)/$", views.tree_json, name="tree-json"),
    url(r"^api/trees/(?P<slug>[-\w]+)/rules/$", views.tree_rules, name="tree-rules"),
    url(r"^api/trees/(?P<slug>[-\w]+)/process/$", views.process_tree, name="process-tree"),
    url(r"^api/annotate/(?P<slug>[-\w]+)/$", views.make_annotations, name="make-annotations"),
    url(r"^api/dictionaries/update/(?P<slug>[-\w]+)/$", views.update_dictionaries, name="update-dictionaries"),
    url(r"^$", views.mortar_home, name="mortar-home"),
]
