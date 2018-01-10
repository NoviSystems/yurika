import django.views.generic
import mortar.models as models
import mortar.forms as forms
import mortar.utils as utils
import mortar.tasks as tasks
import subprocess
import os
import psutil
import datetime, json, uuid
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Count
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.mixins import LoginRequiredMixin
from celery.task.control import revoke
from celery.result import AsyncResult

class ConfigureView(LoginRequiredMixin, django.views.generic.TemplateView):
    template_name = 'mortar/configure.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        analysis,created = models.Analysis.objects.get_or_create(id=0)
        source,created = models.ElasticIndex.objects.get_or_create(name="source")
        dest,created = models.ElasticIndex.objects.get_or_create(name="dest")
        crawler,created = models.Crawler.objects.get_or_create(name="default", category="web", index=source)
        mindmap,created = models.Tree.objects.get_or_create(name="default", slug="default", doc_source_index=source, doc_dest_index=dest)
        query,created = models.Query.objects.get_or_create(name="default")
        analysis.crawler = crawler
        analysis.mindmap = mindmap
        analysis.query = query
        analysis.status = utils.test_status(analysis)
        analysis.save()
        context['analysis'] = analysis
        context['crawler'] = crawler
        context['mindmap'] = mindmap
        tree_json,flat_tree = utils.get_json_tree(mindmap.nodes.all())
        context['tree_json'] = json.dumps(tree_json)
        context['tree_list'] = json.dumps(flat_tree)
        context['query'] = query
        context['seed_list'] = [[seed.urlseed.url,seed.pk] for seed in crawler.seed_list.all()]
        context['dict_path'] = os.path.join(settings.BASE_DIR, settings.DICTIONARIES_PATH)
        context['dictionaries'] = models.Dictionary.objects.all()
        context['dict_list'] = utils.get_dict_list()
        context['form'] = forms.ConfigureForm()
        context['crawl_conf'] = True if crawler.seed_list.all() else False
        context['mm_conf'] = True if mindmap.nodes.all() else False
        context['dict_conf'] = True if context['dictionaries'] else False
        context['query_conf'] = True if query.parts.all() else False
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        form = forms.ConfigureForm(request.POST, request.FILES)
        val = request.POST.get('save')
        if val == 'crawler' and context['crawler'].seed_list.all():
            context['analysis'].status = 1
            context['crawl_conf'] = True
        elif val == 'mindmap':
            context['analysis'].status = 2
            context['mm_conf'] = True
        elif val == 'dicts':
            context['analysis'].status = 3
            context['dict_conf'] = True
        context['analysis'].save()
        return render(request, self.template_name, context=context)

class AnalyzeView(LoginRequiredMixin, django.views.generic.TemplateView):
    template_name = 'mortar/execute.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        analysis,created = models.Analysis.objects.get_or_create(id=0)
        context['analysis'] = analysis
        return context

class AnalysisStatus(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
        return Response(json.dumps({'analysis': analysis.pk, 'state': analysis.status}))

class CrawlerStatus(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        try:
            analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))

            crawler = analysis.crawler
            index = crawler.index.name
            es = settings.ES_CLIENT
            count = es.count(index=index).get('count')
            return Response(json.dumps({'analysis': analysis.pk, 'status': crawler.status, 'count': count}))
        except:
            return Response(json.dumps({'analysis': 0, 'status': 0, 'count': 0}))

class PreprocessStatus(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        try:
            analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
            mindmap = analysis.mindmap
            source = mindmap.doc_source_index.name
            dest = mindmap.doc_dest_index.name
            es = settings.ES_CLIENT
            s_count = es.count(index=source).get('count')
            d_count = es.count(index=dest, doc_type="doc").get('count')
            return Response(json.dumps({'analysis': analysis.pk, 'status': 0 if mindmap.process_id else 1, 'count': d_count, 'source': s_count}))
        except:
            return Response(json.dumps({'analysis': 0, 'status': 0, 'count': 0, 'source': 0}))

class QueryStatus(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        try: 
            analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
            query = analysis.query
            count = models.Annotation.objects.get(query=query).count()
            return Response(json.dumps({'analysis': analysis.pk, 'status': 0 if query.process_id else 1, 'count': count }))
        except:
            return Response(json.dumps({'analysis': 0, 'status': 0, 'count': 0 }))

class StartAnalysis(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
        if analysis.status == 4 or analysis.status > 7:
            tasks.analyze.delay(analysis.pk)
            return HttpResponseRedirect(reverse('analyze'))
        else:
            return HttpResponseRedirect(reverse('configure'))

class StopAnalysis(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
        if analysis.status == 5:
            if analysis.crawler.process_id:
                revoke(analysis.crawler.process_id, terminate=True)
                analysis.crawler.process_id = None
                analysis.crawler.finished_at = datetime.datetime.now()
                analysis.crawler.status = 2
                analysis.crawler.save()
        if analysis.status == 6:
            if analysis.mindmap.process_id:
                revoke(analysis.mindmap.process_id, terminate=True)
                analysis.mindmap.process_id = None
                analysis.mindmap.finished_at = datetime.datetime.now()
                analysis.mindmap.save()
        if analysis.status == 7:
            if analysis.query.process_id:
                revoke(analysis.query.process_id, terminate=True)
                analysis.query.process_id=None
                analysis.query.finished_at = datetime.datetime.now()
                analysis.query.save()
                
        analysis.status = 9
        analysis.finished_at = datetime.datetime.now()
        analysis.save()
        return HttpResponseRedirect(reverse('analyze'))

class DestroyAnalysis(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
        if analysis.mindmap:
            analysis.mindmap.delete()
        if analysis.crawler:
            analysis.crawler.delete()
        if analysis.query:
            analysis.query.delete()
        annotations = models.Annotation.objects.filter(analysis_id=analysis.id)
        annotations.delete()
        analysis.delete()
        return HttpResponseRedirect(reverse('configure'))
        
class UploadMindMapApi(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        mindmap = models.Tree.objects.get(pk=self.kwargs.get('pk'))
        if request.FILES.get('file'):
            utils.read_mindmap(mindmap, request.FILES['file'].read())
            utils.associate_tree(mindmap)
        return HttpResponseRedirect(reverse('configure'))

class EditNodeApi(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        node = models.Node.objects.get(pk=self.kwargs.get('pk'))
        node.name = request.POST.get('name')
        node.regex = request.POST.get('regex')
        node.save()
        return HttpResponseRedirect(reverse('configure'))

class DeleteNodeApi(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        node = models.Node.objects.get(pk=self.kwargs.get('pk'))
        node.delete()
        return HttpResponseRedirect(reverse('configure'))

class AddSeedsApi(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        crawler = models.Crawler.objects.get(pk=self.kwargs.get('pk'))
        seeds = request.POST.get('seed_list').split('\n')
        for seed in seeds:
            if len(seed):
                useed, created = models.URLSeed.objects.get_or_create(url=seed.strip())
                crawler.seed_list.add(useed)
        return HttpResponseRedirect(reverse('configure'))

class EditSeedApi(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        seed = models.URLSeed.objects.get(pk=self.kwargs.get('pk'))
        seed.url = request.POST.get('url')
        seed.save()
        return HttpResponseRedirect(reverse('configure'))

class DeleteSeedApi(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        seed = models.URLSeed.objects.get(pk=self.kwargs.get('pk'))
        seed.delete()
        return HttpResponseRedirect(reverse('configure'))

class AddDictionaryApi(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        name = request.POST.get('dict_name')
        words = request.POST.get('words').split('\n')
        clean = [word.replace("&#13;",'').replace('&#10;', '').strip() for word in words]
        d_words = clean.join('\n')
        new_dict = models.Dictionary.objects.create(name=name, filepath=os.sep.join([settings.DICTIONARIES_PATH, slugify(name) + ".txt"]), words=d_words)
        d.save()
        return HttpResponseRedirect(reverse('configure'))

class EditDictionaryApi(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        dic = models.Dictionary.objects.get(pk=self.kwargs.get('pk'))

        words = request.POST.get('words').split('\n')
        clean = [word.replace("&#13;",'').replace('&#10;', '').strip() for word in words]
        d.words = clean.join('\n')
        d.save()
        return HttpResponseRedirect(reverse('configure'))

class DeleteDictionaryApi(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        dic = models.Dictionary.objects.get(pk=self.kwargs.get('pk'))
        dic.delete()
        return HttpResponseRedirect(reverse('configure'))

class UpdateQueryApi(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        type_list = ['regex', 'dictionary', 'part_of_speech']
        query = models.Query.objects.get(pk=self.kwargs.get('pk'))
        query.parts.all().delete()
        query.category = request.POST.get('category')
        types = request.POST.getlist('part_type')
        oplist = request.POST.getlist('op')
        parts = []
        if len(types) == 1:
            part_list = request.POST.getlist(type_list[int(types[0])])
            querypart = utils.create_query_part(type_list[int(types[0])], part_list[0], query, op=None)
            string = type_list[int(types[0])] + ': ' + querypart.name
            query.string = string
            query.elastic_json = utils.create_query_from_part(types[0], querypart)
            query.save()
        else:
            dicts = request.POST.getlist('dictionary')
            regs = request.POST.getlist('regex')
            pos = request.POST.getlist('part_of_speech')
            string = ''
            for count in range(0,len(types)):
                if count > 0:
                    op = oplist[count-1]
                    string = '(' + string
                else:
                    op = oplist[count]
                part_type = int(types[count])
                part_list = regs
                if part_type == 1:
                    part_list = dicts
                if part_type == 2:
                    part_list = pos
                part_id = part_list.pop(0)
                querypart = utils.create_query_part(type_list[part_type], part_id, query, op=op)
                opname = 'AND' if op else 'OR'
                if count == 0:
                    string += type_list[part_type] + '.' + part_id + ' ' + opname + ' '
                elif count == 1:
                    string += type_list[part_type] + '.' + part_id + ') '
                else:
                    string += opname + ' ' + type_list[part_type] + '.' + part_id + ')'
            string += ')'
            query.string = string
            query.elastic_json = utils.create_query_from_string(string)
            query.save()
        if query.parts.all():
            analysis = models.Analysis.objects.get(pk=0)
            analysis.status = 4
            analysis.save()
        return HttpResponseRedirect(reverse('configure'))

class DictionaryUpdateView(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        tasks.sync_dictionaries.delay()
        return HttpResponseRedirect(reverse('configure'))

class Home(django.views.generic.TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        analysis,created = models.Analysis.objects.get_or_create(pk=0)
        if analysis.status < 5:
            return HttpResponseRedirect(reverse('configure'))
        else:
            return HttpResponseRedirect(reverse('analyze'))

configure = ConfigureView.as_view()
analyze = AnalyzeView.as_view()
start_analysis = StartAnalysis.as_view()
stop_analysis = StopAnalysis.as_view()
destroy_analysis = DestroyAnalysis.as_view()
analysis_status = AnalysisStatus.as_view()
crawler_status = CrawlerStatus.as_view()
preprocess_status = PreprocessStatus.as_view()
query_status = QueryStatus.as_view()
edit_seed = EditSeedApi.as_view()
delete_seed = DeleteSeedApi.as_view()
edit_node = EditNodeApi.as_view()
delete_node = DeleteNodeApi.as_view()
edit_dict = EditDictionaryApi.as_view()
delete_dict = DeleteDictionaryApi.as_view()
add_dict = AddDictionaryApi.as_view()
add_seeds = AddSeedsApi.as_view()
update_query = UpdateQueryApi.as_view()
upload_mindmap = UploadMindMapApi.as_view()
update_dictionaries = DictionaryUpdateView.as_view()
home = Home.as_view()
