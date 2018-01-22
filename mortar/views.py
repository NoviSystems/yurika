import django.views.generic
import mortar.models as models
import mortar.forms as forms
import mortar.utils as utils
import mortar.tasks as tasks
import subprocess
import os
import psutil
import json, uuid
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Count
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from scrapy.crawler import CrawlerProcess
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
        if not crawler.seed_list.all():
            analysis.crawler_configured = False
        if not mindmap.nodes.all():
            analysis.mindmap_configured = False
        if not models.Dictionary.objects.all():
            analysis.dicts_configured = False
        if not query.parts.all():
            analysis.query_configured = False
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
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        form = forms.ConfigureForm(request.POST, request.FILES)
        val = request.POST.get('save')
        if val == 'crawler' and context['crawler'].seed_list.all():
            context['analysis'].crawler_configured = True
        elif val == 'mindmap' and context['mindmap'].nodes.all():
            context['analysis'].mindmap_configured = True
        elif val == 'dicts' and context['dictionaries']:
            context['analysis'].dicts_configured = True
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
        crawler = analysis.crawler
        mindmap = analysis.mindmap
        query = analysis.query
        es = settings.ES_CLIENT

        annotation_count = models.Annotation.objects.using('explorer').filter(query_id=query.id).count()
        return Response(json.dumps({
            'analysis': analysis.pk,
            'crawler': {
                'running': analysis.crawler_running,
                'status': crawler.status,
                'count': crawler.count,
                'errors': list(map(str, crawler.errors)),
            },
            'preprocess': {
                'running': analysis.preprocess_running,
                'status': 0 if mindmap.process_id else 1,
                'n_processed': mindmap.n_processed,
                'n_total': mindmap.n_total,
                'errors': list(map(str, mindmap.errors)),
            },
            'query': {
                'running': analysis.query_running,
                'status': query.status,
                'count': annotation_count,
                'errors': list(map(str, query.errors)),
            },

            #TODO: These are duplicates of the above. Consider removing them
            'crawler_running': analysis.crawler_running,
            'preprocess_running': analysis.preprocess_running,
            'query_running': analysis.query_running,
        }))

class CrawlerStatus(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        try:
            analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))

            crawler = analysis.crawler
            index = crawler.index.name
            es = settings.ES_CLIENT
            count = es.count(index=index).get('count')
            return Response(json.dumps({'analysis': analysis.pk, 'status': crawler.status, 'count': count, 'errors': crawler.errors}))
        except:
            return Response(json.dumps({'analysis': 0, 'status': 0, 'count': 0, 'errors': []}))

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
            count = models.Annotation.objects.using('explorer').filter(query_id=query.id).count()
            return Response(json.dumps({'analysis': analysis.pk, 'status': 0 if query.process_id else 1, 'count': count }))
        except:
            return Response(json.dumps({'analysis': 0, 'status': 0, 'count': 0 }))

class StartAnalysis(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
        if analysis.all_configured:
            if not analysis.any_running:

                # Chain together tasks, so if crawler is killed manually, the
                # other tasks proceed after.
                chain = tasks.run_crawler.signature((analysis.crawler.pk,), immutable=True) \
                      | tasks.preprocess.signature((analysis.mindmap.pk,), immutable=True) \
                      | tasks.run_query.signature((analysis.query.pk,), immutable=True)
                chain()

            return HttpResponseRedirect(reverse('analyze'))
        else:
            return HttpResponseRedirect(reverse('configure'))

class StopAnalysis(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        analysis = models.Analysis.objects.get(pk=self.kwargs.get('pk'))
        if analysis.crawler_running:
            if analysis.crawler.process_id:
                revoke(analysis.crawler.process_id, terminate=True)
                analysis.crawler.process_id = None
                analysis.crawler.finished_at = timezone.now()
                analysis.crawler.status = 2
                analysis.crawler.save()
        if analysis.preprocess_running:
            if analysis.mindmap.process_id:
                revoke(analysis.mindmap.process_id, terminate=True)
                analysis.mindmap.process_id = None
                analysis.mindmap.finished_at = timezone.now()
                analysis.mindmap.save()
        if analysis.query_running:
            if analysis.query.process_id:
                revoke(analysis.query.process_id, terminate=True)
                analysis.query.process_id=None
                analysis.query.finished_at = timezone.now()
                analysis.query.save()
                
        analysis.finished_at = timezone.now()
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
        annotations = models.Annotation.objects.using('explorer').filter(analysis_id=analysis.id)
        annotations.delete()
        analysis.delete()
        es = settings.ES_CLIENT
        es.indices.delete(index='source', ignore=[400, 404])
        es.indices.delete(index='dest', ignore=[400, 404])
        return HttpResponseRedirect(reverse('configure'))
        
class StartCrawler(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        crawler = models.Crawler.objects.get(pk=self.kwargs.get('pk'))
        if not crawler.process_id:
            tasks.run_crawler.delay(crawler.pk)
        return HttpResponseRedirect(reverse('analyze'))

class StopCrawler(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        crawler = models.Crawler.objects.get(pk=self.kwargs.get('pk'))
        if crawler.process_id:
            revoke(crawler.process_id, terminate=True)
            crawler.process_id = None
            crawler.save()
        return HttpResponseRedirect(reverse('analyze'))

class StartPreprocess(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        mindmap = models.Tree.objects.get(pk=self.kwargs.get('pk'))
        if not mindmap.process_id:
            tasks.preprocess.delay(mindmap.pk)
        return HttpResponseRedirect(reverse('analyze'))

class StopPreprocess(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        mindmap = models.Tree.objects.get(pk=self.kwargs.get('pk'))
        if mindmap.process_id:
            revoke(mindmap.process_id)
            mindmap.process_id=None
            mindmap.save()
        return HttpResponseRedirect(reverse('analyze'))

class StartQuery(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        query = models.Query.objects.get(pk=self.kwargs.get('pk'))
        if not query.process_id:
            tasks.run_query.delay(query.pk)
        return HttpResponseRedirect(reverse('analyze'))

class StopQuery(LoginRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        query = models.Query.objects.get(pk=self.kwargs.get('pk'))
        if query.process_id:
            revoke(query.process_id)
            query.process_id=None
            query.save()
        return HttpResponseRedirect(reverse('analyze'))

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
        dic.words = '\n'.join(clean)
        dic.save()
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
        part_list = request.POST.getlist(type_list[int(types[0])])
        if len(types) == 1 and len(part_list):
            if part_list[0]:
                querypart = utils.create_query_part(type_list[int(types[0])], part_list[0], query, op=None)
                string = type_list[int(types[0])] + ': ' + querypart.name
                query.string = string
                query.elastic_json = utils.create_query_from_part(type_list[int(types[0])], querypart)
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
            analysis.query_configured = True
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
        if not analysis.all_configured:
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
start_crawler = StartCrawler.as_view()
stop_crawler = StopCrawler.as_view()
start_preprocess = StartPreprocess.as_view()
stop_preprocess = StopPreprocess.as_view()
start_query = StartQuery.as_view()
stop_query = StopQuery.as_view()
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
