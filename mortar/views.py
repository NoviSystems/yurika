# uncompyle6 version 2.12.0
# Python bytecode 3.5 (3351)
# Decompiled from: Python 2.7.13 (default, Jan 19 2017, 14:48:08) 
# [GCC 6.3.0 20170118]
# Embedded file name: /home/mejohn/itng/yurika/mortar/views.py
# Compiled at: 2017-10-01 19:24:54
# Size of source mod 2**32: 16771 bytes
import django.views.generic
import mortar.models as models
import mortar.forms as forms
import mortar.utils as utils
import subprocess
import os
import psutil
import datetime
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Count
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.mixins import LoginRequiredMixin

class CrawlerView(django.views.generic.TemplateView):
    template_name = 'mortar/crawlers.html'

    def get_context_data(self, *args, **kwargs):
        context = super(CrawlerView, self).get_context_data(*args, **kwargs)
        context['crawlers'] = models.Crawler.objects.all()
        context['new_crawler_form'] = forms.CrawlerForm()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        form = forms.CrawlerForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            new_crawler = models.Crawler.objects.create(name=cd['name'], category=cd['category'], index=cd['index'], status='Stopped')
            seeds = request.POST.get('seed_list').split('\n')
            new_seeds = []
            if cd['category'] == 'txt':
                for seed in seeds:
                    fseed, created = models.FileSeed.objects.get_or_create(path=seed.strip())
                    new_seeds.append(fseed)

            elif cd['category'] == 'web':
                for seed in seeds:
                    useed, created = models.URLSeed.objects.get_or_create(url=seed.strip())
                    new_seeds.append(useed)

            new_crawler.seed_list.set(new_seeds)
        all_crawlers = models.Crawler.objects.all()
        for crawler in all_crawlers:
            if request.POST.get(str(crawler.pk) + '-toggle') == 'start':
                pass
            if crawler.category == 'web':
                crawler_dir = os.path.realpath(os.path.dirname('mortar'))
                crawler_path = os.path.join(crawler_dir, 'mortar/web_crawler.py')
                crawler_cmd = ['python', crawler_path, crawler.name, crawler.index.name, '--urls']
                for u in crawler.seed_list.all():
                    crawler_cmd.append(u.urlseed.url)

                p = subprocess.Popen(crawler_cmd, cwd='/home/mejohn/itng/yurika/mortar/')
                crawler.process_id = p.pid
                crawler.started_at = datetime.datetime.now()
                crawler.status = 'Running'
                crawler.save()
            elif request.POST.get(str(crawler.pk) + '-toggle') == 'stop':
                if psutil.pid_exists(crawler.process_id):
                    proc = psutil.Process(pid=crawler.process_id)
                    proc.terminate()
                crawler.process_id = 0
                crawler.finished_at = datetime.datetime.now()
                crawler.status = 'Stopped'
                crawler.save()

        return render(request, self.template_name, context=context)


class TreeListView(django.views.generic.TemplateView):
    template_name = 'mortar/tree_list.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeListView, self).get_context_data(**kwargs)
        context['trees'] = models.Tree.objects.all()
        context['new_tree_form'] = forms.TreeForm()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.TreeForm(request.POST, self.request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            new_tree = models.Tree.objects.create(name=cd['name'], slug=slugify(cd['name']), doc_source_index=cd['doc_source'], doc_dest_index=cd['doc_dest'])
            if self.request.FILES['file']:
                utils.read_mindmap(new_tree, request.FILES['file'].read())
        return render(request, self.template_name, context=context)


class TreeDetailView(django.views.generic.TemplateView):
    template_name = 'mortar/tree_detail.html'
    selected_node = None

    def get_context_data(self, *args, **kwargs):
        context = super(TreeDetailView, self).get_context_data(**kwargs)
        tree = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        context['user'] = self.request.user
        context['tree'] = tree
        context['tree_json_url'] = reverse('tree-json', kwargs={'slug': tree.slug})
        context['insert_at_url'] = reverse('node-insert', kwargs={'slug': tree.slug})
        context['edit_url'] = reverse('node-edit', kwargs={'slug': tree.slug})
        context['dict_url'] = reverse('dictionaries')
        context['app_label'] = 'yurika'
        context['model_name'] = 'node'
        context['tree_auto_open'] = 'true'
        context['autoescape'] = 'true'
        context['use_context_menu'] = 'false'
        context['elastic_url'] = settings.ES_URL + 'filter_' + tree.slug + '/_search?pretty=true'
        context['importform'] = forms.MindMapImportForm(self.request.POST, self.request.FILES)
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = context['importform']
        if request.POST.get('target_id'):
            instance = models.Node.objects.get(pk=request.POST.get('selected_id'))
            target_id = request.POST.get('target_id')
            position = request.POST.get('position')
            target_instance = models.Node.objects.get(pk=target_id)
            self.move_node(instance, position, target_instance)
        elif form.is_valid():
            utils.read_mindmap(context['tree'], request.FILES['file'].read())
        return render(request, self.template_name, context=self.get_context_data(**kwargs))

    @transaction.atomic()
    def move_node(self, instance, position, target_instance):
        if position == 'before':
            instance.move_to(target_instance, 'left')
        elif position == 'after':
            instance.move_to(target_instance, 'right')
        else:
            if position == 'inside':
                instance.move_to(target_instance)
            else:
                raise Exception('Unknown position')
            instance.save()


class TreeEditView(django.views.generic.FormView, LoginRequiredMixin):
    form_class = forms.TreeEditForm
    template_name = 'mortar/tree_edit.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeEditView, self).get_context_data(**kwargs)
        context['tree'] = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        return context

    def form_valid(self, form, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        tree = context['tree']
        tree.name = form.cleaned_data['name']
        tree.slug = form.cleaned_data['slug']
        tree.save()
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'slug': tree.slug}))


class TreeJsonApi(APIView, LoginRequiredMixin):

    def get(self, request, format=None, **kwargs):
        tree = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        qs = models.Node.objects.filter(tree_link=tree)
        return Response(utils.get_json_tree(qs))


class TreeQueryView(django.views.generic.TemplateView, LoginRequiredMixin):
    template_name = 'mortar/tree_query.html'


class TreeProcessView(APIView, LoginRequiredMixin):
    pass


class NodeInsertView(django.views.generic.FormView, LoginRequiredMixin):
    form_class = forms.NodeForm
    template_name = 'mortar/node_insert.html'

    def get_context_data(self, *args, **kwargs):
        context = super(CategoryInsertView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['tree'] = Tree.objects.get(slug=self.kwargs.get('slug'))
        context['insert_at'] = models.Node.objects.get(id=self.kwargs.get('id'))
        return context

    def form_valid(self, form, format=None, **kwargs):
        context = self.get_context_data(**kwargs)
        node = models.Node(name=form.cleaned_data['name'], regex=form.cleaned_data['regex'], tree_link=context['tree'])
        node.insert_at(context['insert_at'], position='first-child', save=False)
        node.save()
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'slug': context['tree'].slug}))


class NodeEditView(django.views.generic.FormView, LoginRequiredMixin):
    form_class = forms.NodeForm
    template_name = 'mortar/node_edit.html'

    def get_context_data(self, *args, **kwargs):
        context = super(NodeEditView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['tree'] = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        node = models.Node.objects.get(id=self.kwargs.get('id'))
        context['edit'] = node
        data = {'name': node.name,'regex': node.regex}
        context['form'] = forms.NodeForm(initial=data)
        return context

    def form_valid(self, form, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['edit'].name = form.cleaned_data['name']
        context['edit'].regex = form.cleaned_data['regex']
        context['edit'].save()
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'slug': context['tree'].slug}))


class AnnotationListView(django.views.generic.TemplateView, LoginRequiredMixin):
    template_name = 'mortar/annotations.html'

    def get_context_data(self, *args, **kwargs):
        context = super(AnnotationListView, self).get_context_data(**kwargs)
        context['tree'] = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        context['form'] = forms.QuerySelectForm()
        context['anno_list'] = models.Annotation.objects.filter(tree=context['tree'])
        context['result_count'] = len(context['anno_list'])
        context['query_results'] = utils.get_anno_json(context['tree'])
        return context

    def post(self, request, *args, **kwargs):
        context = super(AnnotationListView, self).get_context_data(**kwargs)
        form = forms.QuerySelectForm(request.POST)
        tree = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        if form.is_valid():
            category = form.cleaned_data['category']
            query = form.cleaned_data['query']
            utils.annotate(tree, category, query)
        return HttpResponseRedirect(reverse('annotations', kwargs={'slug': tree.slug}))


class DictionaryListView(django.views.generic.TemplateView, LoginRequiredMixin):
    template_name = 'mortar/dictionaries.html'

    def get_context_data(self, *args, **kwargs):
        context = super(DictionaryListView, self).get_context_data(*args, **kwargs)
        context['dict_list'] = models.Dictionary.objects.all()
        return context


class DictionaryUpdateView(APIView, LoginRequiredMixin):

    def get(self, request, *args, **kwargs):
        utils.update_dictionaries()
        try:
            tree = models.Tree.objects.get(slug=self.kwargs.get('slug'))
            utils.associate_tree(tree)
            return HttpResponseRedirect(reverse('annotation-list', kwargs={'slug': tree.slug}))
        except:
            return HttpResponseRedirect(reverse('dictionaries'))


class QueryCreateView(django.views.generic.TemplateView, LoginRequiredMixin):
    template_name = 'mortar/query.html'

    def get_context_data(self, *args, **kwargs):
        context = super(QueryCreateView, self).get_context_data(**kwargs)
        tree = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        context['tree'] = tree
        context['dict_form'] = forms.DictionaryPartForm()
        context['regex_form'] = forms.RegexPartForm()
        context['subquery_form'] = forms.SubQueryPartForm()
        context['pos_form'] = forms.PartOfSpeechPartForm()
        return context

    def create_query_part(self, qtype, qid, op, query):
        if not op:
            op = '+'
        if qtype == 'dictionary':
            dictionary = models.Dictionary.objects.get(id=qid)
            part = models.DictionaryPart.objects.create(query=query, dictionary=dictionary, op=op, name=dictionary.name)
            return part
        if qtype == 'regex':
            regex = models.Node.objects.get(id=qid)
            part = models.RegexPart.objects.create(query=query, regex=regex, op=op, name=regex.name)
            return part
        if qtype == 'subquery':
            subquery = models.Query.objects.get(id=qid)
            part = models.SubQueryPart.objects.create(query=query, subquery=subquery, op=op, name=subquery.name)
            return part
        if qtype == 'part_of_speech':
            name = ''
            for part in PARTS_OF_SPEECH:
                if part[0] == qid:
                    name = part[1]

            part = models.PartOfSpeechPart.objects.create(query=query, part_of_speech=qid, op=op, name=name)
            return part

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        first_type = request.POST.get('form_type_1')
        sec_type = request.POST.get('form_type_2')
        op = request.POST.get('op')
        if first_type and sec_type and op:
            query = models.Query.objects.create()
            first_list = request.POST.getlist(first_type)
            sec_list = request.POST.getlist(sec_type)
            first_part = utils.create_query_part(first_type, first_list[0], op, query)
            sec_part = utils.create_query_part(sec_type, sec_list[1], op, query)
            query.name = '(' + first_part.name + ' ' + op + ' ' + sec_part.name + ')'
            query.string = '(' + first_type + '.' + first_list[0] + ' ' + op + ' ' + sec_type + '.' + sec_list[1] + ')'
            query.save()
            query.elastic_json = utils.create_query_from_string(query.string)
            query.save()
            return HttpResponseRedirect(reverse('annotations', kwargs={'slug': context['tree'].slug}))
        if first_type and not sec_type:
            first_list = request.POST.getlist(first_type)
            query = models.Query.objects.create()
            first_part = utils.create_query_part(first_type, first_list[0], op, query)
            if first_part:
                query.name = first_part.name
                if first_type == 'dictionary':
                    query.elastic_json = json.dumps(utils.make_dict_query(models.Dictionary.objects.get(id=first_list[0])))
                else:
                    if first_type == 'regex':
                        query.elastic_json = json.dumps(utils.make_regex_query(models.Node.objects.get(id=first_list[0])))
                    elif first_type == 'part_of_speech':
                        query.elastic_json = json.dumps(utils.make_pos_query(first_list[0]))
                    query.save()
            else:
                query.delete()
            return HttpResponseRedirect(reverse('annotation-list', kwargs={'slug': context['tree'].slug}))
        return render(request, self.template_name, context=self.get_context_data(**kwargs))

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        context['dict_form'].fields['dictionary'].queryset = models.Dictionary.objects.all()
        context['regex_form'].fields['regex'].queryset = models.Node.objects.filter(tree_link=models.Tree.objects.get(slug=self.kwargs.get('slug')), regex__isnull=False)
        context['subquery_form'].fields['subquery'].queryset = models.Query.objects.annotate(num_parts=Count('parts')).filter(num_parts__gt=1)
        return self.render_to_response(context)


class Home(django.views.generic.TemplateView):
    template_name = 'home.html'


crawlers = CrawlerView.as_view()
trees = TreeListView.as_view()
tree_detail = TreeDetailView.as_view()
tree_json = TreeJsonApi.as_view()
tree_edit = TreeEditView.as_view()
tree_filter = TreeQueryView.as_view()
tree_process = TreeProcessView.as_view()
node_insert = NodeInsertView.as_view()
node_insert_at = NodeInsertView.as_view()
node_edit = NodeEditView.as_view()
node_edit_at = NodeEditView.as_view()
annotations = AnnotationListView.as_view()
dictionaries = DictionaryListView.as_view()
update_dictionaries = DictionaryUpdateView.as_view()
query = QueryCreateView.as_view()
home = Home.as_view()
# okay decompiling views.cpython-35.pyc
