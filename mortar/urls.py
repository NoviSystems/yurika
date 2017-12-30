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
 url('^dictionaries/update/$', views.update_dictionaries, name='update-dicts'),
 url('^nodes/edit/(?P<pk>[\\d]+)/$', views.edit_node, name="edit-node-pk"),
 url('^nodes/edit/$', views.edit_node, name="edit-node"),
 url('^nodes/delete/$', views.delete_node, name="delete-node"),
 url('^nodes/delete/(?P<pk>[\\d]+)/$', views.delete_node, name="delete-node-pk"),
 url('^seeds/edit/(?P<pk>[\\d]+)/$', views.edit_seed, name="edit-seed-pk"),
 url('^seeds/edit/$', views.edit_seed, name="edit-seed"),
 url('^seeds/delete/(?P<pk>[\\d]+)/$', views.delete_seed, name="delete-seed-pk"),
 url('^seeds/delete/$', views.delete_seed, name="delete-seed"),
 url('^dicts/edit/(?P<pk>[\\d]+)/$', views.edit_dict, name="edit-dict-pk"),
 url('^dicts/edit/$', views.edit_dict, name="edit-dict"),
 url('^dicts/delete/(?P<pk>[\\d]+)/$', views.delete_dict, name="delete-dict-pk"),
 url('^dicts/delete/$', views.delete_dict, name="delete-dict"),
 url('^$', views.home, name='home')
]
