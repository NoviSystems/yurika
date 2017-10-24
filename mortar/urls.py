from django.conf.urls import url
from . import views
urlpatterns = [
 url('^crawlers/$', views.crawlers, name='crawlers'),
 url('^mindmaps/$', views.trees, name='trees'),
 url('^mindmaps/(?P<slug>[-\\w]+)/$', views.tree_detail, name='tree-detail'),
 url('^mindmaps/(?P<slug>[-\\w]+)/edit/$', views.tree_edit, name='tree-edit'),
 url('^mindmaps/(?P<slug>[-\\w]+)/json/$', views.tree_json, name='tree-json'),
 url('^mindmaps/(?P<slug>[-\\w]+)/insert/(?P<id>[\\d]+)/$', views.node_insert, name='node-insert-at'),
 url('^mindmaps/(?P<slug>[-\\w]+)/insert/$', views.node_insert, name='node-insert'),
 url('^mindmaps/(?P<slug>[-\\w]+)/edit/(?P<id>[\\d]+)/$', views.node_edit, name='node-edit-at'),
 url('^mindmaps/(?P<slug>[-\\w]+)/edit/$', views.node_insert, name='node-edit'),
 url('^mindmaps/(?P<slug>[-\\w]+)/filter/$', views.tree_filter, name='tree-filter'),
 url('^mindmaps/(?P<slug>[-\\w]+)/process/$', views.tree_process, name='tree-process'),
 url('^dictionaries/$', views.dictionaries, name='dictionaries'),
 url('^dictionaries/(?P<pk>[\\d]+)/$', views.dictionary_detail, name='dictionary-detail'),
 url('^dictionaries/update/$', views.update_dictionaries, name='update-dicts'),
 url('^dictionaries/update/(?P<slug>[-\\w]+)/$', views.update_dictionaries, name='update-dictionaries'),
 url('^annotations/(?P<slug>[-\\w]+)/$', views.annotations, name='annotations'),
 url('^query/(?P<slug>[-\\w]+)/$', views.query, name='query'),
 url('^$', views.home, name='home')]
