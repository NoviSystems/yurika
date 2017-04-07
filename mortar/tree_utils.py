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
        node_info = dict(
            label=cat.name,
            id=pk,
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

def search_elastic(tree):
    results = {}
    es = settings.ES_CLIENT
    regex_list = get_regex_list(tree)
    return results
