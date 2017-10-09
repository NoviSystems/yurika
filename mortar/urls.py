# uncompyle6 version 2.12.0
# Python bytecode 3.5 (3351)
# Decompiled from: Python 2.7.13 (default, Jan 19 2017, 14:48:08) 
# [GCC 6.3.0 20170118]
# Embedded file name: /home/mejohn/itng/yurika/mortar/urls.py
# Compiled at: 2017-09-29 11:19:27
# Size of source mod 2**32: 1703 bytes
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
 url('^dictionaries/update/$', views.update_dictionaries, name='update-dicts'),
 url('^dictionaries/update/(?P<slug>[-\\w]+)/$', views.update_dictionaries, name='update-dictionaries'),
 url('^annotations/(?P<slug>[-\\w]+)/$', views.annotations, name='annotations'),
 url('^query/(?P<slug>[-\\w]+)/$', views.query, name='query'),
 url('^$', views.home, name='home')]
# okay decompiling urls.cpython-35.pyc
