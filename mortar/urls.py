from django.conf.urls import url
from . import views
urlpatterns = [
 url('^configure/$', views.configure, name='configure'),
 url('^analyze/$', views.analyze, name='analyze'),
 url('^analyze/start/(?P<pk>[\\d]+)/$', views.start_analysis, name="start-analysis"),
 url('^analyze/stop/(?P<pk>[\\d]+)/$', views.stop_analysis, name="stop-analysis"),
 url('^analyze/destroy/(?P<pk>[\\d]+)/$', views.destroy_analysis, name="destroy-analysis"),
 url('^status/crawler/(?P<pk>[\\d]+)/$', views.crawler_status, name="crawler-status"),
 url('^status/preprocess/(?P<pk>[\\d]+)/$', views.preprocess_status, name="preprocess-status"),
 url('^status/query/(?P<pk>[\\d]+)/$', views.query_status, name="query-status"),
 url('^$', views.home, name='home')
]
''' url('^crawlers/$', views.crawlers, name='crawlers'),
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
 url('^mindmaps/(?P<slug>[-\\w]+)/check/$', views.tree_process_check, name='process-check'),
 url('^dictionaries/$', views.dictionaries, name='dictionaries'),
 url('^dictionaries/(?P<pk>[\\d]+)/$', views.dictionary_detail, name='dictionary-detail'),
 url('^dictionaries/update/$', views.update_dictionaries, name='update-dicts'),
 url('^dictionaries/update/(?P<slug>[-\\w]+)/$', views.update_dictionaries, name='update-dictionaries'),
 url('^annotations/$', views.annotation_trees, name='annotation-trees'),
 url('^annotations/(?P<slug>[-\\w]+)/$', views.annotations, name='annotations'),
 url('^query/(?P<pk>[\\d]+)/$', views.query, name='query'),
]'''
