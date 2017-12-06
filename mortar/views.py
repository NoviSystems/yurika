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

class CrawlerView(LoginRequiredMixin, django.views.generic.TemplateView):
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
                tasks.start_crawler.delay(crawler.pk)
            elif request.POST.get(str(crawler.pk) + '-toggle') == 'stop':
                if crawler.process_id:
                    revoke(crawler.process_id, terminate=True)
                crawler.process_id = None
                crawler.finished_at = datetime.datetime.now()
                crawler.status = 'Stopped'
                crawler.save()

        return render(request, self.template_name, context=context)

class TreeListView(LoginRequiredMixin, django.views.generic.TemplateView):
    template_name = 'mortar/tree_list.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeListView, self).get_context_data(**kwargs)
        context['trees'] = models.Tree.objects.all()
        context['form'] = forms.TreeForm()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.TreeForm(request.POST, self.request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            new_tree = models.Tree.objects.create(name=cd['name'], slug=slugify(cd['name']), doc_source_index=cd['doc_source'], doc_dest_index=cd['doc_dest'])
            if self.request.FILES.get('file'):
                utils.read_mindmap(new_tree, request.FILES['file'].read())
                utils.associate_tree(new_tree)
        for tree in context['trees']:
            if request.POST.get(str(tree.pk) + '-delete'):
                tree.delete()
                context['trees'] = models.Tree.objects.all()
            elif request.POST.get(str(tree.pk) + '-duplicate'):
                new_tree = models.Tree.objects.create(
                    name=tree.name + " (copy)",
                    slug=slugify(uuid.uuid1()),
                    doc_dest_index=tree.doc_dest_index,
                    doc_source_index=tree.doc_source_index
                )
                utils.copy_nodes(tree, new_tree)
                context['trees'] = models.Tree.objects.all()

        return render(request, self.template_name, context=context)


class TreeDetailView(LoginRequiredMixin, django.views.generic.TemplateView):
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
        elif form.is_valid() and not request.POST.get('export'):
            utils.read_mindmap(context['tree'], request.FILES['file'].read())
            utils.associate_tree(context['tree'])
        elif request.POST.get('export'):
            print("Exporting")
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


class TreeEditView(LoginRequiredMixin, django.views.generic.UpdateView):
    template_name = 'mortar/tree_edit.html'
    form_class = forms.TreeEditForm
    model = models.Tree
    context_object_name = 'tree'

    def get_success_url(self):
        return reverse('tree-detail', kwargs={'slug': self.object.slug})

class TreeJsonApi(LoginRequiredMixin, APIView):

    def get(self, request, format=None, **kwargs):
        tree = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        qs = models.Node.objects.filter(tree_link=tree)
        return Response(utils.get_json_tree(qs))


class TreeQueryView(LoginRequiredMixin, django.views.generic.TemplateView):
    template_name = 'mortar/tree_query.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeQueryView, self).get_context_data(**kwargs)
        tree = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        context['tree'] = tree
        context['tree_json_url'] = reverse('tree-json', kwargs={'slug': tree.slug})
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        tree = context['tree']
        doc_filter = {'names': [], 'regexs': []}
        for node in models.Node.objects.filter(tree_link=tree):
            if request.POST.get(str(node.id) + '-add'):
                if node.regex:
                    doc_filter['regexs'].append(node.regex)
                elif node.dictionary:
                    words = node.dictionary.words.all()
                    doc_filter['names'].extend([w.name for w in words])
                else:
                    doc_filter['names'].append(node.name)
        tasks.preprocess.delay(tree.pk, doc_filter)
        messages.info(request, 'Tree filtering and reindexing started in background')
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'slug': context['tree'].slug}))

class TreeProcessView(LoginRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        tree = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        tasks.preprocess.delay(tree.pk, {'names':[], 'regexs':[]})
        messages.info(request, 'Tree filtering and reindexing started in background')
        return HttpResponseRedirect(reverse('annotations', kwargs={'slug': tree.slug}))


class NodeInsertView(LoginRequiredMixin, django.views.generic.FormView):
    form_class = forms.NodeForm
    template_name = 'mortar/node_edit.html'

    def get_context_data(self, *args, **kwargs):
        context = super(NodeInsertView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['tree'] = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        if self.kwargs.get('id'):
            context['insert_at'] = models.Node.objects.get(id=self.kwargs.get('id'))
            context['name'] = context['insert_at'].name + ' >'
        else:
            context['insert_at'] = None
        return context

    def form_valid(self, form, format=None, **kwargs):
        context = self.get_context_data(**kwargs)
        node = models.Node(name=form.cleaned_data['name'], regex=form.cleaned_data['regex'], tree_link=context['tree'])
        if context['insert_at']:
            node.insert_at(context['insert_at'], position='first-child', save=False)
        else:
            node.parent = None
        node.save()
        utils.associate_tree(context['tree'])
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'slug': context['tree'].slug}))


class NodeEditView(LoginRequiredMixin, django.views.generic.FormView):
    form_class = forms.NodeForm
    template_name = 'mortar/node_edit.html'

    def get_context_data(self, *args, **kwargs):
        context = super(NodeEditView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['tree'] = models.Tree.objects.get(slug=self.kwargs.get('slug'))
        node = models.Node.objects.get(id=self.kwargs.get('id'))
        context['edit'] = node
        context['name'] = node.name
        data = {'name': node.name,'regex': node.regex}
        context['form'] = forms.NodeForm(initial=data)
        return context

    def form_valid(self, form, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['edit'].name = form.cleaned_data['name']
        context['edit'].regex = form.cleaned_data['regex']
        context['edit'].save()
        utils.associate_tree(context['tree'])
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'slug': context['tree'].slug}))


class AnnotationListView(LoginRequiredMixin, django.views.generic.TemplateView):
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
            tasks.run_query.delay(tree.pk, category, query.pk)
        return HttpResponseRedirect(reverse('annotations', kwargs={'slug': tree.slug}))

class AnnotationTreeView(LoginRequiredMixin, django.views.generic.TemplateView):
    template_name = 'mortar/annotation_trees.html'

    def get_context_data(self, *args, **kwargs):
        context = super(AnnotationTreeView, self).get_context_data(*args, **kwargs)
        context['trees'] = models.Tree.objects.all()
        return context

class DictionaryListView(LoginRequiredMixin, django.views.generic.TemplateView):
    template_name = 'mortar/dictionaries.html'

    def get_context_data(self, *args, **kwargs):
        context = super(DictionaryListView, self).get_context_data(*args, **kwargs)
        context['dict_list'] = models.Dictionary.objects.all()
        context['form'] = forms.DictionaryForm()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.DictionaryForm(request.POST)
        if form.is_valid():
            new_dict = models.Dictionary.objects.create(name=form.cleaned_data['name'], filepath=os.sep.join([settings.DICTIONARIES_PATH, slugify(form.cleaned_data['name']) + ".txt"]))
            words = form.cleaned_data['words'].split('\n')
            for word in words:
                if len(word):
                    new_word = models.Word.objects.create(name=word, dictionary=new_dict)
            utils.write_to_new_dict(new_dict)
        return render(request, self.template_name, context=self.get_context_data(**kwargs))

class DictionaryDetailView(LoginRequiredMixin, django.views.generic.TemplateView):
    template_name = 'mortar/dictionary_detail.html'

    def get_context_data(self, *args, **kwargs):
        context = super(DictionaryDetailView, self).get_context_data(**kwargs)
        context['dict'] = models.Dictionary.objects.get(id=self.kwargs.get('pk'))
        context['words'] = context['dict'].words.all()
        context['nodes'] = context['dict'].nodes.all()
        context['form'] = forms.WordForm()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.WordForm(request.POST)
        if form.is_valid():
            new_word = models.Word.objects.create(name=form.cleaned_data['name'], dictionary=context['dict'])
        return render(request, self.template_name, context=self.get_context_data(**kwargs))

class DictionaryUpdateView(LoginRequiredMixin, APIView):

    def get(self, request, *args, **kwargs):
        tasks.sync_dictionaries.delay()
        slug = self.kwargs.get('slug')
        if slug:
            tree = models.Tree.objects.get(slug=self.kwargs.get('slug'))
            utils.associate_tree(tree)
            return HttpResponseRedirect(reverse('annotations', kwargs={'slug': tree.slug}))
        return HttpResponseRedirect(reverse('dictionaries'))


class QueryCreateView(LoginRequiredMixin, django.views.generic.TemplateView):
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

            return HttpResponseRedirect(reverse('annotations', kwargs={'slug': context['tree'].slug}))
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
annotation_trees = AnnotationTreeView.as_view()
dictionaries = DictionaryListView.as_view()
update_dictionaries = DictionaryUpdateView.as_view()
dictionary_detail = DictionaryDetailView.as_view()
query = QueryCreateView.as_view()
home = Home.as_view()
