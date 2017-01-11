import time
from django.forms import forms
from django.views.generic import TemplateView, ListView, FormView
from django.utils.text import slugify 
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.db import transaction
from django.shortcuts import render
from xml.etree import ElementTree as etree
from django_mptt_admin.admin import DjangoMpttAdminMixin
from django_mptt_admin.util import *
from mptt.templatetags.mptt_tags import cache_tree_children
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from .models import Project, ProjectTree, Category
from .forms import TreeForm, ImportForm, CategoryForm
import re

class ProjectListView(ListView):
    model = Project
    context_object_list = 'project_list'

class ProjectDetailView(FormView):
    template_name = 'mortar/project_detail.html'
    form_class = TreeForm

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)    
        trees = context['project_trees']
        for tree in trees:
            if request.GET.get(str(tree.pk) + ('-duplicate')) == "True":
                new_tree = ProjectTree(
                    name=tree.name + " (copy)",
                    slug=slugify(tree.name+" (copy)"),
                    project=context['project']
                )
                new_tree.save()
                self.copy_nodes(tree, new_tree)

            elif request.GET.get(str(tree.pk) + ('-delete')) == "True":
                tree.delete()

        context['project_trees'] = context['project'].trees.all()
        return self.render_to_response(context)
    
    def get_context_data(self, *args, **kwargs):
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        context['project'] = Project.objects.get(slug=self.kwargs.get('slug'))
        context['project_trees'] = context['project'].trees.all()
        return context

    def form_valid(self, form, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        new_tree = ProjectTree(
            name=form.cleaned_data['name'],
            slug=slugify(form.cleaned_data['name']),
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
                new_node = Category.objects.create(
                    name=node.name,
                    parent=parent,
                    projecttree=new_tree,
                    is_rule=node.is_rule,
                    regex=node.regex
                )    
                new_node.save()

class TreeDetailView(TemplateView):
    template_name = 'mortar/tree_detail.html'
    selected_node = None

    def get_context_data(self, *args, **kwargs):
        context = super(TreeDetailView, self).get_context_data(**kwargs)
        tree = ProjectTree.objects.get(slug=self.kwargs.get('slug'))
        context['tree'] = tree
        context['tree_json_url'] = reverse('tree-json', kwargs={'slug': tree.slug})
        context['insert_at_url'] = reverse('tree-insert', kwargs={'project_slug': self.kwargs.get('project_slug'), 'slug': tree.slug})
        context['edit_url'] = reverse('tree-edit', kwargs={'project_slug': self.kwargs.get('project_slug'), 'slug': tree.slug})
        context['app_label'] = "mortar"
        context['model_name'] = "category"
        context['tree_auto_open'] = 'true'
        context['autoescape'] = 'true'
        context['use_context_menu'] = 'false'
        #context['paths'] = self.get_all_paths(tree)
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
        elif form.is_valid():
            if request.FILES['file'].name.split('.')[-1] == 'mm':
                self.read_mindmap(context['tree'], request.FILES['file'].read())
            else:
                self.read_csv(context['tree'], request.FILES['file'].read())

        return render(request, self.template_name, context=self.get_context_data(**kwargs))

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

    def read_csv(self, tree, csvfile):
        upload = csvfile.decode().split('\n')[1:]
        paths = self.get_all_paths(tree)
        new_rules = self.preprocess_csv(csvfile)
        created = 0
        with transaction.atomic():
            for key in new_rules.keys():
                print("Processing " + str(len(upload)) + " new records")
                parent, all_paths = self.create_categories(key, tree, paths)
                for rule in new_rules[key]:
                    self.create_rule(parent, tree, rule['name'], rule['regex'])
                    created += 1
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

    def unroll_csv(self, csvfile):
        unrolled = {}
        upload = csvfile.decode().split('\n')[1:]
        for line in upload:
            csv = line.strip('\r').split(',')
            if len(csv) == 3:
                path = csv[0].split('.')
                for x in range(0, len(path)):
                    pass
#    def rule_exists(self, tree, name, regex, path):
#        rules = Category.objects.filter(projecttree=tree, is_rule=True, name=name, regex=regex)
#        for rule in rules:
#            print("%s %s" % (rule.full_path_name, path))
#            if rule.full_path_name == path:
#                return True
#        return False
    
    def get_all_paths(self, tree):
        leaves = Category.objects.filter(children__isnull=True, projecttree=tree)
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
        # TODO see if any part of new_path exists
        #for path in all_paths:
        #    if new_path.startswith(path):       
        #        a = new_path.split('.')
        #        b = path.split('.')
        #        c = set(a) - set(b)
        #        cats = [cat for cat in a if cat in c]
        #        print("Set Difference")
        #        print(cats)

        # create any categories that need creating
        last_cat = None
        for cat in cats:
            new_cat,created = Category.objects.get_or_create(projecttree=tree, name=cat, parent=last_cat)
            print(new_cat)
            if created:
                print("New Category: %s" % cat)
                if new_cat.full_path_name not in all_paths:
                    all_paths.append(new_path)
                new_cat.save()
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

class TreeJsonApi(APIView):
        
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
                    

class TreeInsertView(FormView):
    form_class = CategoryForm
    template_name = 'mortar/tree_insert.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeInsertView, self).get_context_data(**kwargs)
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
        print(context)
        node.insert_at(context['insert_at'], position="first-child", save=False)
        print(node.parent)
        node.save()
        return HttpResponseRedirect(reverse('tree-detail', kwargs={'project_slug':context['project_slug'], 'slug':context['tree'].slug}))

class TreeEditView(FormView):
    form_class = CategoryForm
    template_name = 'mortar/tree_insert.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TreeEditView, self).get_context_data(**kwargs)
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
tree_insert = TreeInsertView.as_view()
tree_edit = TreeInsertView.as_view()
