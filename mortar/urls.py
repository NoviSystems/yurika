# Copyright (c) 2018, North Carolina State University
# 
#All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
# 
# 3. The names "North Carolina State University", "NCSU" and any trade‐name, personal name, trademark, trade device, service mark, symbol, image, icon, or any abbreviation, contraction or simulation thereof owned by North Carolina State University must not be used to endorse or promoteproducts derived from this software without prior written permission. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 

from django.conf.urls import url
from . import views
urlpatterns = [
 url('^configure/$', views.configure, name='configure'),
 url('^configure/clear/(?P<pk>[\\d]+)/$', views.clear_config, name='clear-config'),
 url('^execute/$', views.analyze, name='analyze'),
 url('^execute/start/(?P<pk>[\\d]+)/$', views.start_analysis, name="start-analysis"),
 url('^execute/stop/(?P<pk>[\\d]+)/$', views.stop_analysis, name="stop-analysis"),
 url('^execute/clear/(?P<pk>[\\d]+)/$', views.clear_results, name="clear-results"),
 url('^status/execute/(?P<pk>[\\d]+)/$', views.analysis_status, name="analysis-status"),
 url('^crawler/start/(?P<pk>[\\d]+)/$', views.start_crawler, name="start-crawler"),
 url('^crawler/stop/(?P<pk>[\\d]+)/$', views.stop_crawler, name="stop-crawler"),
 url('^preprocess/start/(?P<pk>[\\d]+)/$', views.start_preprocess, name="start-preprocess"),
 url('^preprocess/stop/(?P<pk>[\\d]+)/$', views.stop_preprocess, name="stop-preprocess"),
 url('^query/start/(?P<pk>[\\d]+)/$', views.start_query, name="start-query"),
 url('^query/stop/(?P<pk>[\\d]+)/$', views.stop_query, name="stop-query"),
 url('^dictionaries/update/$', views.update_dictionaries, name='update-dicts'),
 url('^nodes/upload/(?P<pk>[\\d]+)/$', views.upload_mindmap, name="upload-mindmap"),
 url('^nodes/edit/(?P<pk>[\\d]+)/$', views.edit_node, name="edit-node-pk"),
 url('^nodes/edit/$', views.edit_node, name="edit-node"),
 url('^nodes/delete/$', views.delete_node, name="delete-node"),
 url('^nodes/delete/(?P<pk>[\\d]+)/$', views.delete_node, name="delete-node-pk"),
 url('^seeds/add/(?P<pk>[\\d]+)/$', views.add_seeds, name="add-seeds"),
 url('^seeds/edit/(?P<pk>[\\d]+)/$', views.edit_seed, name="edit-seed-pk"),
 url('^seeds/edit/$', views.edit_seed, name="edit-seed"),
 url('^seeds/delete/(?P<pk>[\\d]+)/$', views.delete_seed, name="delete-seed-pk"),
 url('^seeds/delete/$', views.delete_seed, name="delete-seed"),
 url('^dicts/add/$', views.add_dict, name="add-dict"),
 url('^dicts/edit/(?P<pk>[\\d]+)/$', views.edit_dict, name="edit-dict-pk"),
 url('^dicts/edit/$', views.edit_dict, name="edit-dict"),
 url('^dicts/delete/(?P<pk>[\\d]+)/$', views.delete_dict, name="delete-dict-pk"),
 url('^dicts/delete/$', views.delete_dict, name="delete-dict"),
 url('^queries/edit/(?P<pk>[\\d]+)/$', views.update_query, name="edit-query"),
 url('^$', views.home, name='home')
]
