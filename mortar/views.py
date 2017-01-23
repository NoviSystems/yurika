import time, os, uuid
from django.forms import forms
from django.views.generic import TemplateView, ListView, FormView
from django.utils.text import slugify 
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from xml.etree import ElementTree as etree
from django_mptt_admin.admin import DjangoMpttAdminMixin
from django_mptt_admin.util import *
from mptt.templatetags.mptt_tags import cache_tree_children
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from wsgiref.util import FileWrapper
import mimetypes
from .models import Project, ProjectTree, Category
from .forms import TreeForm, TreeEditForm, ImportForm, CategoryForm
import re

class ProjectListView(ListView, LoginRequiredMixin):
    model = Project
    context_object_list = 'project_list'

    def get_queryset(self):
        return Project.objects.filter(assigned=self.request.user)

class ProjectDetailView(FormView, LoginRequiredMixin):
    template_name = 'mortar/project_detail.html'
    form_class = TreeForm

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
        context['user'] = self.request.user
        context['project'] = Project.objects.get(slug=self.kwargs.get('slug'))
        context['project_users'] = context['project'].assigned.all()
        context['project_trees'] = ProjectTree.objects.filter(project=context['project'])
        return context

    def form_valid(self, form, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        new_tree = ProjectTree(
            name=form.cleaned_data['name'],
            slug=slugify(form.cleaned_data['slug']),
            owner=self.request.user,
            project=context['project']
        )
        new_tree.save()
        if form.cleaned_data['populate']:
            default_tree = ProjectTree.objects.get(slug="default")
            self.copy_nodes(default_tree, new_tree)
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug':context['project'].slug, 'slug':new_tree.slug}))

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
                        is_rule=node.is_rule,
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
        context['tree_json_url'] = reverse('tree-json', kwargs={'slug': tree.slug})
        context['insert_at_url'] = reverse('cat-insert', kwargs={'project_slug': tree.project.slug, 'slug': tree.slug})
        context['branch_url'] = reverse('tree-branch', kwargs={'project_slug': tree.project.slug, 'slug': tree.slug})
        context['edit_url'] = reverse('cat-edit', kwargs={'project_slug': tree.project.slug, 'slug': tree.slug})
        context['app_label'] = "mortar"
        context['model_name'] = "category"
        context['tree_auto_open'] = 'true'
        context['autoescape'] = 'true'
        context['use_context_menu'] = 'false'
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
                self.read_mindmap(context['tree'], request.FILES['file'].read())
            else:
                self.read_csv(context['tree'], request.FILES['file'].read())
        return render(request, self.template_name, context=self.get_context_data(**kwargs))

    def tree_to_csv(self):
        context = self.get_context_data()
        tree = context['tree']
        filename = tree.slug + ".csv"
        with open(filename, "w") as f:
            f.write("fullPathName,name,regex\n")
            for cat in Category.objects.filter(projecttree=tree, is_rule=True):
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

    def read_mindmap(self, tree, mmstring):
        root = etree.fromstring(mmstring)
        
        for child in root.iter():
            print(child.tag, child.attrib)

    def read_csv(self, tree, csvfile):
        upload = csvfile.decode().split('\n')[1:]
        paths = self.get_all_paths(tree)
        new_rules = self.preprocess_csv(csvfile)
        created = 0
        for key in new_rules.keys():
            print("Processing " + str(len(upload)) + " new records")
            parent, all_paths = self.create_categories(key, tree, paths)
            #to_create = []
            for rule in new_rules[key]:
                #to_create.append(Category(parent=parent, projecttree=tree, name=rule['name'], is_rule=True, regex=rule['regex']))
                self.create_rule(parent, tree, rule['name'], rule['regex'])
                created += 1

            #with transaction.atomic():
            #    Category.objects.bulk_create(to_create)
                print(str(created) + "/" + str(len(upload)) + " records processed")
            paths = all_paths

    def preprocess_csv(self, csvfile):
        processed = {}
        upload = csvfile.decode().split('\n')[1:]
        for line in upload:
            csv = line.strip('\r').split(',')
            if len(csv) == 3:
                if csv[0] not in processed:
                    processed[csv[0]] = [{"name": csv[1], "regex": csv[2]}]
                else:
                    processed[csv[0]].append({"name": csv[1], "regex": csv[2]})
        return processed

    def get_all_paths(self, tree):
        leaves = Category.objects.filter(projecttree=tree)
        paths = []
        for leaf in leaves:
            path = leaf.full_path_name
            if path not in paths:
                paths.append(path)
        return paths

    def create_categories(self, new_path, tree, all_paths):
        cats = new_path.split('.')
        # check if new_path already exists, fastest
        if new_path in all_paths:
            filtered = [x for x in tree.categories.all() if x.full_path_name == new_path]
            if len(filtered) > 0:
                return filtered[0],all_paths

        # create any categories that need creating
        last_cat = None
        for cat in cats:
            with transaction.atomic():
                new_cat,created = Category.objects.get_or_create(projecttree=tree, name=cat, parent=last_cat)
            if created:
                print("New Category: %s" % cat)
                if new_cat.full_path_name not in all_paths:
                    all_paths.append(new_path)
            last_cat = new_cat
        return last_cat,all_paths

    def create_rule(self, parent, tree, name, regex):
        try:
            re.compile(regex)
            rule,created = Category.objects.get_or_create(projecttree=tree,
                                                          is_rule=True,
                                                          name=name,
                                                          regex=regex,
                                                          parent=parent)
            if created:
                print("New Rule: %s" % regex)
        except re.error:
            print("%s: Invalid Regex" % name)
            raise forms.ValidationError("Invalid Regex")

class TreeJsonApi(APIView, LoginRequiredMixin):
        
    def get(self, request, format=None, **kwargs):
        tree = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        qs = Category.objects.filter(projecttree=tree)
        return Response(self.get_json_from_queryset(qs))
    
    def get_json_from_queryset(self, qs, max_level=None):
        # adopted from django_mptt_admin.utils, adding in more fields for nodes
        pk_attname = 'id'
        tree = []
        node_dict = dict()
        min_level = None
        for cat in qs:
            if min_level is None:
                min_level = cat.level
            pk = getattr(cat, pk_attname)
            node_info = dict(
                label=cat.name,
                id=pk,
                is_rule=cat.is_rule,
                regex=cat.regex
            )

            if max_level is not None and not cat.is_leaf_node():
                node_info['load_on_demand'] = True

            if cat.level == min_level:
                tree.append(node_info)
            else:
                parent_id = cat.parent_id
                parent_info = node_dict.get(parent_id)
                if parent_info:
                    if 'children' not in parent_info:
                        parent_info['children'] = []
                    parent_info['children'].append(node_info)
                    if max_level is not None:
                        parent_info['load_on_demand'] = False
            node_dict[pk] = node_info
        return tree
                    
class TreeRegexApi(APIView, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        tree = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        nodes = Category.objects.filter(projecttree=tree)
        regexs = []
        for node in nodes:
            if node.is_rule:
                regexs.append(node.regex)
        return Response(regexs)

class CategoryInsertView(FormView, LoginRequiredMixin):
    form_class = CategoryForm
    template_name = 'mortar/tree_insert.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeInsertView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['project_slug'] = self.kwargs.get('project_slug')
        context['tree'] = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        context['insert_at'] = Category.objects.get(id=self.kwargs.get('id'))
        return context

    def form_valid(self, form, format=None, **kwargs):
        context = self.get_context_data(**kwargs)
        #parent = Category.objects.get(id=int(context['insert_at']))
        node = Category(
            name=form.cleaned_data['name'],
            is_rule=form.cleaned_data['is_rule'],
            regex=form.cleaned_data['regex'],
        #    parent=parent,
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
                is_rule=node.is_rule,
                regex=node.regex
            )                                                                   
            new_node.save()
 
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug': project.slug, 'slug': new_tree.slug}))

class CategoryEditView(FormView, LoginRequiredMixin):
    form_class = CategoryForm
    template_name = 'mortar/tree_insert.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeEditView, self).get_context_data(**kwargs)
        context['user'] = self.request.user
        context['project_slug'] = self.kwargs.get('project_slug')
        context['tree'] = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        context['edit'] = Category.objects.get(id=self.kwargs.get('id'))
        return context

    def form_valid(self, form, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['edit'].name = form.cleaned_data['name']
        context['edit'].is_rule = form.cleaned_data['is_rule']
        context['edit'].regex = form.cleaned_data['regex']
        context['edit'].save() 
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug':context['project_slug'], 'slug':context['tree'].slug}))

class Home(TemplateView):
    template_name = "home.html"

home = Home.as_view()
project_list = ProjectListView.as_view()
project_detail = ProjectDetailView.as_view()
tree_detail = TreeDetailView.as_view()
tree_json = TreeJsonApi.as_view()
tree_rules = TreeRegexApi.as_view()
tree_edit = TreeEditView.as_view()
cat_insert = CategoryInsertView.as_view()
cat_edit = CategoryInsertView.as_view()
tree_branch = TreeBranchView.as_view()
