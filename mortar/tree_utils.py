from django.db import transaction
from xml.etree import ElementTree as etree
from .models import ProjectTree, Category
from django.conf import settings
import urllib.request
import simplejson, json


def get_regex_list(tree):
    nodes = Category.objects.filter(projecttree=tree)
    regexes = []
    for node in nodes:
        if node.regex:
            regexes.append(node.regex)
        else:
            regexes.append(node.name)
    return regexes

def get_json_tree(queryset, max_level=None):
    # adopted from django_mptt_admin.utils, adding in more fields for nodes     
    pk_attname = 'id'
    tree = []
    node_dict = dict()
    min_level = None
    for cat in queryset:
        if min_level is None:
            min_level = cat.level
        pk = getattr(cat, pk_attname)

        try:
            dict_id=cat.dictionary.id
        except:
            dict_id=None

        node_info = dict(
            label=cat.name,
            id=pk,
            regex=cat.regex,
            dictionary=dict_id
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

def search_solr(tree):
    solr = settings.SOLR_URL + "?wt=json"
    regex_list = get_regex_list(tree)
    results = {}
    for regex in regex_list:   
        docs = {}
        req = urllib.request.Request(solr)
        query = json.dumps({'params': {'q': 'content:/'+regex+"/", 'df': 'content'}}).encode('utf-8')
        req.add_header('Content-Length', len(query))
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, data=query) as f:
            resp = simplejson.load(f)
            docs['count'] = int(resp['response']['numFound'])
            if docs['count'] > 0:
                docs['docs'] = []
                for entry in resp['response']['docs']:
                    doc = {'url': entry['url'], 'content': entry['content']}
                docs['docs'].append(doc)                                    
        results[regex] = docs
    return results

def read_mindmap(tree, mmstring):
    root = etree.fromstring(mmstring)
                
    for child in root:
        name = child.attrib.get('TEXT')
        if len(name) > 0 and child.tag=='node':
            node,created = Category.objects.get_or_create(
                name=name,
                projecttree=tree,
                parent=None
            )
            create_mm_children(child, node, tree)
        else:
            create_mm_children(child, None, tree)
            
def create_mm_children(xmlparent, nodeparent, tree):
    children = xmlparent.getchildren()
    for child in children: 
        if child.tag=='node':
            name = child.attrib.get('TEXT')
            node,created = Category.objects.get_or_create(
                name=name,
                projecttree=tree,
                parent=nodeparent
            )
            if len(child.getchildren()) > 0:
                create_mm_children(child, node, tree)

def read_csv(tree, csvfile):                                                                                                                                    
    upload = csvfile.decode().split('\n')[1:]
    paths = get_all_paths(tree)
    new_rules = preprocess_csv(csvfile)
    created = 0
    for key in new_rules.keys():
        print("Processing " + str(len(upload)) + " new records")
        parent, all_paths = create_categories(key, tree, paths)
        #to_create = []
        for rule in new_rules[key]:
            create_rule(parent, tree, rule['name'], rule['regex'])
            created += 1
            print(str(created) + "/" + str(len(upload)) + " records processed")
        paths = all_paths
        
def preprocess_csv(csvfile):
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

def get_all_paths(tree):
    leaves = Category.objects.filter(projecttree=tree)
    paths = []
    for leaf in leaves: 
        path = leaf.full_path_name
        if path not in paths:
            paths.append(path)
    return paths

def create_categories(new_path, tree, all_paths):
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

def create_rule(parent, tree, name, regex):
    try:
        re.compile(regex)
        rule,created = Category.objects.get_or_create(projecttree=tree,
                name=name,
                regex=regex,
                parent=parent)
        if created:
            print("New Rule: %s" % regex)             
    except re.error:
        print("%s: Invalid Regex" % name)
        raise forms.ValidationError("Invalid Regex")
