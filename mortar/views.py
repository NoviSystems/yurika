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
        crawler,created = models.Crawler.objects.get_or_create(name="default", category="web", index=source, status=2)
        mindmap,created = models.Tree.objects.get_or_create(name="default", slug="default", doc_source_index=source, doc_dest_index=dest)
        query,created = models.Query.objects.get_or_create(name="default")
        analysis.crawler = crawler
        analysis.mindmap = mindmap
        analysis.query = query
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
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        print(request.POST)
        form = forms.ConfigureForm(request.POST, request.FILES)
        if request.POST.get('crawler') == 'submit':
            seeds = request.POST.get('seed_list').split('\n')
            for seed in seeds:
                if len(seed):
                    useed, created = models.URLSeed.objects.get_or_create(url=seed.strip())
                    context['crawler'].seed_list.add(useed)
            context['seed_list'] = [(seed.urlseed.url,seed.pk) for seed in context['crawler'].seed_list.all()]
        if request.POST.get('mindmap') == 'submit':
            if self.request.FILES.get('file'):
                utils.read_mindmap(context['mindmap'], request.FILES['file'].read())
                utils.associate_tree(context['mindmap'])
        if request.POST.get('new_dict') == 'submit':
            name = request.POST.get('dict_name')
            words = request.POST.get('words').split('\n')
            new_dict = models.Dictionary.objects.create(name=name, filepath=os.sep.join([settings.DICTIONARIES_PATH, slugify(name) + ".txt"]))
            with transaction.atomic():
                for word in words:
                    clean = word.replace("&#13;",'').replace('&#10;', '').strip()
                    w,created = models.Word.objects.get_or_create(name=clean, dictionary=new_dict)
        if request.POST.get('query') == 'submit':
            type_list = ['regex', 'dictionary', 'part_of_speech']
            query = context['query']
            query.parts.all().delete()
            query.category = request.POST.get('category')
            types = request.POST.getlist('part_type')
            oplist = request.POST.getlist('op')
            parts = []
            if len(types) == 1:
                part_list = request.POST.getlist(type_list[int(types[0])])
                querypart = utils.create_query_part(type_list[int(types[0])], part_list[0], query, op=None)
                string = type_list[int(types[0])] + ': ' + querypart.name
                query.name = string[:50]
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
                query.name = string[:50]
                query.string = string
                query.elastic_json = utils.create_query_from_string(string)
                query.save()
        return render(request, self.template_name, context=context)

class AnalyzeView(LoginRequiredMixin, django.views.generic.TemplateView):
    template_name = 'mortar/analyze.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        analysis,created = models.Analysis.objects.get_or_create(id=0)
        context['analysis'] = analysis
        return context

class CrawlerStatus(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        try:
            analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))

            crawler = analysis.crawler
            index = crawler.index.name
            es = settings.ES_CLIENT
            count = es.count(index=index).get('count')
            return Response(json.dumps({'status': crawler.status, 'count': count}))
        except:
            return Response(json.dumps({}))

class PreprocessStatus(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        try:
            analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
            mindmap = analysis.mindmap
            source = mindmap.doc_source_index.name
            dest = mindmap.doc_dest_index.name
            es = settings.ES_CLIENT
            s_count = es.count(index=source).get('count')
            d_count = es.count(index=dest).get('count')
            return Response(json.dumps({'status': 0 if mindmap.process_id else 1, 'count': d_count, 'source': s_count}))
        except:
            return Response(json.dumps({}))

class QueryStatus(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        try: 
            analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
            query = analysis.query
            count = models.Annotation.objects.get(query=query).count()
            return Response(json.dumps({'status': 0 if query.process_id else 1, 'count': count }))
        except:
            return Response(json.dumps({}))

class StartAnalysis(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
        if analysis.status:
            tasks.analyze.delay(analysis.pk)
            return HttpResponseRedirect(reverse('analyze'))
        else:
            return HttpResponseRedirect(reverse('configure'))

class StopAnalysis(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
        if analysis.status == 2:
            if analysis.crawler.process_id:
                revoke(analysis.crawler.process_id, terminate=True)
                analysis.crawler.process_id = None
                analysis.crawler.finished_at = datetime.datetime.now()
                analysis.crawler.status = 2
                analysis.crawler.save()
        if analysis.status == 3:
            if analysis.mindmap.process_id:
                revoke(analysis.mindmap.process_id, terminate=True)
                analysis.mindmap.process_id = None
                analysis.mindmap.finished_at = datetime.datetime.now()
                analysis.mindmap.save()
        if analysis.status == 4:
            if analysis.query.process_id:
                revoke(analysis.query.process_id, terminate=True)
                analysis.query.process_id=None
                analysis.query.finished_at = datetime.datetime.now()
                analysis.query.save()
                
        analysis.status = 6
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

class EditSeedApi(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        seed = models.URLSeed.objects.get(pk=self.kwargs.get('pk'))
        print(request.POST)
        seed.url = request.POST.get('url')
        seed.save()
        return HttpResponseRedirect(reverse('configure'))

class DeleteSeedApi(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        seed = models.URLSeed.objects.get(pk=self.kwargs.get('pk'))
        seed.delete()
        return HttpResponseRedirect(reverse('configure'))

class EditDictionaryApi(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        dic = models.Dictionary.objects.get(pk=self.kwargs.get('pk'))

        words = request.POST.get('words').split('\n')
        print(request.POST.get('words'))
        dic_words = dic.words.all()
        new_words = []
        with transaction.atomic():
            for word in words:
                clean = word.replace("&#13;",'').replace('&#10;', '').strip()
                w,created = models.Word.objects.get_or_create(name=clean, dictionary=dic)
                new_words.append(w)
        
            for word in dic_words:
                if word not in new_words:
                   word.delete()
        return HttpResponseRedirect(reverse('configure'))

class DeleteDictionaryApi(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        dic = models.Dictionary.objects.get(pk=self.kwargs.get('pk'))
        words = dic.words.all()
        words.delete()
        dic.delete()
        return HttpResponseRedirect(reverse('configure'))


class QueryCreateView(LoginRequiredMixin, django.views.generic.TemplateView):
    template_name = 'mortar/query.html'

    def get_context_data(self, *args, **kwargs):
        context = super(QueryCreateView, self).get_context_data(**kwargs)
        analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
        tree = analysis.mindmap
        context['tree'] = tree
        context['dict_form'] = forms.DictionaryPartForm()
        context['regex_form'] = forms.RegexPartForm()
        context['subquery_form'] = forms.SubQueryPartForm()
        context['pos_form'] = forms.PartOfSpeechPartForm()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        print(request.POST)
        oplist = request.POST.getlist('op')
        count = len(oplist)
        print(count)
        if count and request.POST.get('form_type_1'):
            query = models.Query.objects.create()
            parts = []
            if count == 1 and not len(oplist[0]):
                part_type = request.POST.get('form_type_1')
                part_list = request.POST.getlist(part_type)
                part_id = part_list[0]
                querypart = utils.create_query_part(part_type, part_id, query, op=None)
                string = part_type + ': ' + querypart.name
                query.name = string[:50]
                query.string = string
                query.elastic_json = utils.create_query_from_part(part_type, querypart)
                query.save()
            else:
                string = ''
                for part in range(0,count+1):
                    part_type = request.POST.get('form_type_' + str(part+1))
                    if part > 0:
                        op = oplist[part-1]
                        string = '(' + string
                    else:
                        op = oplist[part]
                    part_list = request.POST.getlist(part_type)
                    part_id = part_list[part]
                    querypart = utils.create_query_part(part_type, part_id, query, op=op)
                    if part == 0:
                        string += part_type + '.' + part_id + ' ' + op + ' '
                    elif part == 1:
                        string += part_type + '.' + part_id + ') '
                    else:
                        string += op + ' ' + part_type + '.' + part_id + ') '

                string += ')'
                query.name = string[:50]
                query.string = string
                query.elastic_json = utils.create_query_from_string(string)
                query.save()

            return HttpResponseRedirect(reverse('configure'))
        return render(request, self.template_name, context=self.get_context_data(**kwargs))

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        context['dict_form'].fields['dictionary'].queryset = models.Dictionary.objects.all()
        context['regex_form'].fields['regex'].queryset = models.Node.objects.filter(tree_link=context['tree'], regex__isnull=False)
        context['subquery_form'].fields['subquery'].queryset = models.Query.objects.annotate(num_parts=Count('parts')).filter(num_parts__gt=1)
        return self.render_to_response(context)

class DictionaryUpdateView(LoginRequiredMixin, APIView):

    def get(self, request, *args, **kwargs):
        tasks.sync_dictionaries.delay()
        return HttpResponseRedirect(reverse('configure'))

class Home(django.views.generic.TemplateView):
    template_name = 'home.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('configure'))

configure = ConfigureView.as_view()
analyze = AnalyzeView.as_view()
start_analysis = StartAnalysis.as_view()
stop_analysis = StopAnalysis.as_view()
destroy_analysis = DestroyAnalysis.as_view()
crawler_status = CrawlerStatus.as_view()
preprocess_status = PreprocessStatus.as_view()
query_status = QueryStatus.as_view()
edit_seed = EditSeedApi.as_view()
delete_seed = DeleteSeedApi.as_view()
edit_node = EditNodeApi.as_view()
delete_node = DeleteNodeApi.as_view()
edit_dict = EditDictionaryApi.as_view()
delete_dict = DeleteDictionaryApi.as_view()
update_dictionaries = DictionaryUpdateView.as_view()
home = Home.as_view()
