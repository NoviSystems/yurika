import time, os, uuid
from django.forms import forms
from django.views.generic import TemplateView, ListView, FormView
from django.utils.text import slugify 
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django_mptt_admin.admin import DjangoMpttAdminMixin
from django_mptt_admin.util import *
from mptt.templatetags.mptt_tags import cache_tree_children
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from wsgiref.util import FileWrapper
import mimetypes
from .models import Project, ProjectTree, Category, AIDictionary, AIDictionaryObject, Annotation, QueryLog
from .forms import ProjectForm, TreeForm, TreeEditForm, ImportForm, CategoryForm, AnnotationQueryForm
import mortar.elastic_utils as elastic_utils
import mortar.tree_utils as tree_utils
import mortar.dictionary_utils as dictionary_utils
import re
import urllib.request, json
import simplejson, requests

class ProjectListView(TemplateView, LoginRequiredMixin):
    template_name = 'mortar/project_list.html'
    
    def get_context_data(self, *args, **kwargs):
        context = super(ProjectListView, self).get_context_data(*args, **kwargs)
        context['project_list'] = Project.objects.filter(assigned=self.request.user)
        context['form'] = ProjectForm(self.request.POST)
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        form = context['form']
        if form.is_valid():
            new_project = Project.objects.create(
                name=form.cleaned_data['name'],
                slug=form.cleaned_data['slug'],
            )
            new_project.assigned = self.request.user
            new_project.save()
            return HttpResponseRedirect(reverse('project-detail', kwargs={'project_slug':new_project.slug}))
        return render(request, self.template_name, context=self.get_context_data(**kwargs))

class ProjectDetailView(TemplateView, LoginRequiredMixin):
    template_name = 'mortar/project_detail.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)    
        trees = context['project_trees']
        for tree in trees:
            if request.GET.get(str(tree.pk) + ('-duplicate')) == "True" and request.user in context['project_users']:
                new_tree = ProjectTree(
                    name=tree.name + " (copy)",
                    slug=slugify(uuid.uuid1()),
                    owner=request.user,
                    project=context['project']
                )
                new_tree.save()
                self.copy_nodes(tree, new_tree)

            elif request.GET.get(str(tree.pk) + ('-delete')) == "True" and request.user == tree.owner:
                tree.delete()

        context['project_trees'] = ProjectTree.objects.filter(project=context['project'])
        return self.render_to_response(context)
    
    def get_context_data(self, *args, **kwargs):
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        context['form'] = TreeForm(self.request.POST, self.request.FILES)
        context['user'] = self.request.user
        context['project'] = Project.objects.get(slug=self.kwargs.get('slug'))
        context['project_users'] = context['project'].assigned.all()
        context['project_trees'] = ProjectTree.objects.filter(project=context['project'])
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = context['form']
        if form.is_valid():
            new_tree = ProjectTree(
                name=form.cleaned_data['name'],
                slug=slugify(form.cleaned_data['slug']),
                owner=self.request.user,
                project=context['project']
            )
            new_tree.save() 
            if request.FILES.get('file') and request.FILES['file'].name.split('.')[-1] == 'mm':
                tree_utils.read_mindmap(new_tree, request.FILES['file'].read())
            elif request.FILES.get('file'):
                tree_utils.read_csv(new_tree, request.FILES['file'].read())
            return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug':context['project'].slug,'slug':new_tree.slug}))
        return render(request, self.template_name, context=self.get_context_data(**kwargs))


    def copy_nodes(self, old_tree, new_tree):
        old_nodes = old_tree.categories.all()
        old_roots = [n for n in old_nodes if n.is_root_node()]
        for root in old_roots:
            branch = root.get_descendants(include_self=True)
            for node in branch:
                parent = None
                if node.parent:
                    possibles = Category.objects.filter(projecttree=new_tree, name=node.parent.name)
                    parent = [p for p in possibles if p.full_path_name==node.parent.full_path_name]
                    parent = parent[0]
                with transaction.atomic():
                    new_node = Category.objects.create(
                        name=node.name,
                        parent=parent,
                        projecttree=new_tree,
                        regex=node.regex
                    )    
                    new_node.save()

class TreeEditView(FormView, LoginRequiredMixin):
    form_class = TreeEditForm
    template_name = 'mortar/tree_edit.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeEditView, self).get_context_data(**kwargs)
        context['tree'] = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        return context

    def form_valid(self, form, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        tree = context['tree']
        project = tree.project
        tree.name=form.cleaned_data['name']
        tree.slug=form.cleaned_data['slug']
        tree.save()
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug':project.slug,'slug':tree.slug}))

class TreeDetailView(TemplateView, LoginRequiredMixin):
    template_name = 'mortar/tree_detail.html'
    selected_node = None

    def get_context_data(self, *args, **kwargs):
        context = super(TreeDetailView, self).get_context_data(**kwargs)
        tree = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        context['user'] = self.request.user
        context['tree'] = tree
        context['project'] = tree.project
        context['tree_json_url'] = reverse('tree-json', kwargs={'slug': tree.slug})
        context['insert_at_url'] = reverse('cat-insert', kwargs={'project_slug': tree.project.slug, 'slug': tree.slug})
        context['branch_url'] = reverse('tree-branch', kwargs={'project_slug': tree.project.slug, 'slug': tree.slug})
        context['edit_url'] = reverse('cat-edit', kwargs={'project_slug': tree.project.slug, 'slug': tree.slug})
        context['dict_url'] = reverse('dictionary-list')
        context['app_label'] = "mortar"
        context['model_name'] = "category"
        context['tree_auto_open'] = 'true'
        context['autoescape'] = 'true'
        context['use_context_menu'] = 'false'
        context['elastic_url'] = settings.ES_URL + 'filter_' + tree.slug + '/_search?pretty=true'
        context['importform'] = ImportForm(self.request.POST, self.request.FILES)
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = context['importform']
        if request.POST.get('target_id'):
            instance = Category.objects.get(pk=request.POST.get('selected_id'))
            target_id = request.POST.get('target_id')
            position = request.POST.get('position')
            target_instance = Category.objects.get(pk=target_id)
            self.move_node(instance, position, target_instance)
        elif request.POST.get('export'):
            return self.tree_to_csv()
        elif form.is_valid():
            if request.FILES['file'].name.split('.')[-1] == 'mm':
                tree_utils.read_mindmap(context['tree'], request.FILES['file'].read())
            else:
                tree_utils.read_csv(context['tree'], request.FILES['file'].read())
        return render(request, self.template_name, context=self.get_context_data(**kwargs))

    def tree_to_csv(self):
        context = self.get_context_data()
        tree = context['tree']
        filename = tree.slug + ".csv"
        with open(filename, "w") as f:
            f.write("fullPathName,name,regex\n")
            for cat in Category.objects.filter(projecttree=tree):
                if cat.is_leaf_node():
                    f.write(",".join([cat.full_path_name, cat.name, cat.regex]) + "\n")
        f = open(filename, 'rb')
        wrapper = FileWrapper(f)
        mt = mimetypes.guess_type(filename)[0]
        response = HttpResponse(wrapper, content_type=mt)
        response['Content-Length'] = os.path.getsize(filename)
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        response['X-Sendfile'] = os.path.realpath(filename)
        return response    

    @transaction.atomic()
    def move_node(self, instance, position, target_instance):
        if position == 'before':
            instance.move_to(target_instance, 'left')
        elif position == 'after':
            instance.move_to(target_instance, 'right')
        elif position == 'inside':
            instance.move_to(target_instance)
        else:
            raise Exception("Unknown position")

        instance.save()

class TreeJsonApi(APIView, LoginRequiredMixin):
    def get(self, request, format=None, **kwargs):
        tree = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        qs = Category.objects.filter(projecttree=tree)
        return Response(tree_utils.get_json_tree(qs))
    
class TreeRegexApi(APIView, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        tree = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        regexs = tree_utils.get_regex_list(tree)
        return Response(regexs)

class CategoryInsertView(FormView, LoginRequiredMixin):
    form_class = CategoryForm
    template_name = 'mortar/tree_insert.html'

    def get_context_data(self, *args, **kwargs):
        context = super(CategoryInsertView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['project_slug'] = self.kwargs.get('project_slug')
        context['tree'] = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        context['insert_at'] = Category.objects.get(id=self.kwargs.get('id'))
        return context

    def form_valid(self, form, format=None, **kwargs):
        context = self.get_context_data(**kwargs)
        node = Category(
            name=form.cleaned_data['name'],
            regex=form.cleaned_data['regex'],
            projecttree=context['tree']
        )
        node.insert_at(context['insert_at'], position="first-child", save=False)
        node.save()
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug':context['project_slug'], 'slug':context['tree'].slug}))

class TreeBranchView(APIView, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        tree = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        project = tree.project
        root = Category.objects.get(id=self.kwargs.get('id'))
        branch = root.get_descendants(include_self=True)
        new_tree = ProjectTree.objects.create(
            name='Branch of ' + str(root.id),
            slug=slugify(uuid.uuid1()),
            owner=request.user,
            project=project,
        )

        for node in branch:
            parent = None
            if node.parent and node != root:
                possibles = Category.objects.filter(projecttree=new_tree, name=node.parent.name)
                parent = [p for p in possibles if p.full_path_name in node.parent.full_path_name]
                parent = parent[0]
            new_node = Category.objects.create(
                name=node.name,
                parent=parent,
                projecttree=new_tree,
                regex=node.regex
            )                                                                   
            new_node.save()
 
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug': project.slug, 'slug': new_tree.slug}))

class CategoryEditView(FormView, LoginRequiredMixin):
    form_class = CategoryForm
    template_name = 'mortar/cat_edit.html'

    def get_context_data(self, *args, **kwargs):
        context = super(CategoryEditView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['project_slug'] = self.kwargs.get('project_slug')
        context['tree'] = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        cat = Category.objects.get(id=self.kwargs.get('id'))
        context['edit'] = cat
        data = {'name': cat.name, 'regex': cat.regex}
        context['form'] = CategoryForm(initial=data)
        return context

    def form_valid(self, form, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['edit'].name = form.cleaned_data['name']
        context['edit'].regex = form.cleaned_data['regex']
        context['edit'].save() 
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug':context['project_slug'], 'slug':context['tree'].slug}))

class TreeQuerySelectView(TemplateView):
    template_name = 'mortar/tree_query.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeQuerySelectView, self).get_context_data(**kwargs)
        context['tree'] = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        context['project'] = context['tree'].project
        context['tree_json_url'] = reverse('tree-json', kwargs={'slug': context['tree'].slug})
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        tree = context['tree']
        and_filter = []
        for node in Category.objects.filter(projecttree=tree):
            if request.POST.get(str(node.id) + '-add'):
                if node.regex:
                    and_filter.append(node.regex)
                else:
                    and_filter.append(node.name)
        query = elastic_utils.build_mortar_query(and_filter)
        elastic_utils.create_index('filter_' + tree.slug)
        elastic_utils.reindex('nutch', 'filter_' + tree.slug, query)
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug':context['project'].slug, 'slug':context['tree'].slug}))

class AnnotationView(TemplateView, LoginRequiredMixin):
    template_name = 'mortar/annotations.html'

    def get_context_data(self, *args, **kwargs):
        context = super(AnnotationView, self).get_context_data(**kwargs)
        context['tree'] = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        context['anno_list'] = Annotation.objects.filter(projecttree=context['tree']).exclude(termvectors=None)
        return context

class AnnotationQueryView(FormView, LoginRequiredMixin):
    template_name = 'mortar/annotation_query.html'
    form_class = AnnotationQueryForm

    def get_form(self, *args, **kwargs):
        form = super(AnnotationQueryView, self).get_form(*args, **kwargs)
        form.fields['regexs'].queryset = Category.objects.filter(projecttree=ProjectTree.objects.get(slug=self.kwargs.get('slug')), regex__isnull=False)
        return form
 
    def get_context_data(self, *args, **kwargs):
        context = super(AnnotationQueryView, self).get_context_data(**kwargs)
        context['tree'] = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        #context['form']['regexs'].choices = Category.objects.filter(projecttree=context['tree'])
        return context

    def form_valid(self, form, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        tree = context['tree']
        cd = form.cleaned_data
        #dictionary_utils.process(tree)
        dictionary_utils.annotate_by_query(tree, cd['annotype'], cd['dictionaries'], cd['andor'], cd['regexs'])

        return HttpResponseRedirect(reverse('annotation-list', kwargs={'slug': context['tree'].slug}))

class AnnotateApi(APIView, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        tree = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        dictionary_utils.associate_tree(tree)
        dictionary_utils.process(tree)
        dictionary_utils.annotate_by_tree(tree, pos)
        return HttpResponseRedirect(reverse('annotation-list', kwargs={'slug':tree.slug}))

class DictionaryDetailView(TemplateView, LoginRequiredMixin):
    template_name = "mortar/dictionary_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = super(DictionaryDetailView, self).get_context_data(*args, **kwargs)
        context['dict'] = AIDictionary.objects.get(id=self.kwargs.get('pk'))
        context['words'] = context['dict'].words.all()
        context['categories'] = context['dict'].categories.all()
        return context

class DictionaryListView(TemplateView, LoginRequiredMixin):
    template_name = "mortar/dictionary_list.html"

    def get_context_data(self, *args, **kwargs):
        context = super(DictionaryListView, self).get_context_data(*args, **kwargs)
        context['dict_list'] = AIDictionary.objects.all()
        return context

class DictionaryUpdateApi(APIView, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        tree = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        dictionary_utils.update_dictionaries()
        dictionary_utils.associate_tree(tree)
        dictionary_utils.process(tree)
        return HttpResponseRedirect(reverse('annotation-list', kwargs={'slug':tree.slug}))

class TermVectorView(TemplateView, LoginRequiredMixin):
    template_name = "mortar/termvectors.html"

    def get_context_data(self, *args, **kwargs):
        context = super(TermVectorView, self).get_context_data(*args, **kwargs)
        context['annotation'] = Annotation.objects.get(id=self.kwargs.get('pk'))
        context['tree'] = context['annotation'].projecttree
        context['termvectors'] = context['annotation'].termvectors.all()
        # all termvectors should have the same document
        context['document'] = context['termvectors'].first().document
        return context

class MortarHome(TemplateView, LoginRequiredMixin):
    template_name = "mortar/home.html"

    def get_context_data(self, *args, **kwargs):
        context= super(MortarHome, self).get_context_data(*args, **kwargs)
        context['project_list'] = Project.objects.all()
        context['form'] = ProjectForm(self.request.POST)
        context['dict_list'] = AIDictionary.objects.all()
        return context


    def post(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        form = context['form']
        if form.is_valid():
            new_project = Project.objects.create(
                name=form.cleaned_data['name'],
                slug=form.cleaned_data['slug'],
            )   
            new_project.assigned = get_user_model().objects.filter(username=self.request.user.username)
            new_project.save()
        return render(request, self.template_name, context=self.get_context_data(**kwargs))

class Home(TemplateView):
    template_name="home.html"

home = Home.as_view()
mortar_home = MortarHome.as_view()
project_list = ProjectListView.as_view()
project_detail = ProjectDetailView.as_view()
tree_detail = TreeDetailView.as_view()
tree_query = TreeQuerySelectView.as_view()
tree_json = TreeJsonApi.as_view()
tree_rules = TreeRegexApi.as_view()
tree_edit = TreeEditView.as_view()
cat_insert = CategoryInsertView.as_view()
cat_edit = CategoryEditView.as_view()
tree_branch = TreeBranchView.as_view()
annotation_list = AnnotationView.as_view()
make_annotations = AnnotateApi.as_view()
annotation_query = AnnotationQueryView.as_view()
dictionary_detail = DictionaryDetailView.as_view()
dictionary_list = DictionaryListView.as_view()
update_dictionaries = DictionaryUpdateApi.as_view()
term_vectors = TermVectorView.as_view()
