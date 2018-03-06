"""
BSD 3-Clause License

Copyright (c) 2018, North Carolina State University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. The names "North Carolina State University", "NCSU" and any trade‐name,
   personal name, trademark, trade device, service mark, symbol, image, icon,
   or any abbreviation, contraction or simulation thereof owned by North
   Carolina State University must not be used to endorse or promoteproducts
   derived from this software without prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from django.conf.urls import url
from django.http import Http404

from . import views


def not_found(request):
    # Used for entries which are only referenced in js to build longer URLs
    # (since you can't use {% url '...' %} in js)
    raise Http404()


urlpatterns = [
    url(r'^configure/$', views.ConfigureView.as_view(), name='configure'),
    url(r'^configure/crawler/$', views.ConfigureCrawlerView.as_view(), name='configure-crawler'),
    url(r'^configure/mindmap/$', views.ConfigureMindMapView.as_view(), name='configure-mindmap'),
    url(r'^configure/dictionaries/$', views.ConfigureDictionariesView.as_view(), name='configure-dictionaries'),
    url(r'^configure/query/$', views.ConfigureQueryView.as_view(), name='configure-query'),

    url(r'^execute/$', views.analyze, name='analyze'),
    url(r'^execute/start/(?P<pk>[\d]+)/$', views.start_analysis, name="start-analysis"),
    url(r'^execute/stop/(?P<pk>[\d]+)/$', views.stop_analysis, name="stop-analysis"),
    url(r'^execute/clear/(?P<pk>[\d]+)/$', views.clear_results, name="clear-results"),
    url(r'^status/execute/(?P<pk>[\d]+)/$', views.analysis_status, name="analysis-status"),
    url(r'^crawler/start/(?P<pk>[\d]+)/$', views.start_crawler, name="start-crawler"),
    url(r'^crawler/stop/(?P<pk>[\d]+)/$', views.stop_crawler, name="stop-crawler"),
    url(r'^preprocess/start/(?P<pk>[\d]+)/$', views.start_preprocess, name="start-preprocess"),
    url(r'^preprocess/stop/(?P<pk>[\d]+)/$', views.stop_preprocess, name="stop-preprocess"),
    url(r'^query/start/(?P<pk>[\d]+)/$', views.start_query, name="start-query"),
    url(r'^query/stop/(?P<pk>[\d]+)/$', views.stop_query, name="stop-query"),
    url(r'^dictionaries/update/$', views.update_dictionaries, name='update-dicts'),
    url(r'^nodes/upload/(?P<pk>[\d]+)/$', views.upload_mindmap, name="upload-mindmap"),
    url(r'^nodes/edit/(?P<pk>[\d]+)/$', views.edit_node, name="edit-node-pk"),
    url(r'^nodes/edit/$', not_found, name="edit-node"),
    url(r'^nodes/delete/$', not_found, name="delete-node"),
    url(r'^nodes/delete/(?P<pk>[\d]+)/$', views.delete_node, name="delete-node-pk"),
    url(r'^seeds/add/(?P<pk>[\d]+)/$', views.add_seeds, name="add-seeds"),
    url(r'^seeds/edit/(?P<pk>[\d]+)/$', views.edit_seed, name="edit-seed-pk"),
    url(r'^seeds/edit/$', not_found, name="edit-seed"),
    url(r'^seeds/delete/(?P<pk>[\d]+)/$', views.delete_seed, name="delete-seed-pk"),
    url(r'^seeds/delete/$', not_found, name="delete-seed"),
    url(r'^dicts/add/$', views.add_dict, name="add-dict"),
    url(r'^dicts/edit/(?P<pk>[\d]+)/$', views.edit_dict, name="edit-dict-pk"),
    url(r'^dicts/edit/$', not_found, name="edit-dict"),
    url(r'^dicts/delete/(?P<pk>[\d]+)/$', views.delete_dict, name="delete-dict-pk"),
    url(r'^dicts/delete/$', not_found, name="delete-dict"),
    url(r'^$', views.home, name='home'),
]
