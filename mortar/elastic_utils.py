from .models import ProjectTree, Category
from django.conf import settings
import urllib.request
import simplejson, json

from elasticsearch.client import IndicesClient
from elasticsearch import helpers

from .tree_utils import get_regex_list

def create_index(name, analysis_conf):
    es = settings.ES_CLIENT
    i_client = IndicesClient(client=es)
    body = analysis_conf
    i_client.create(index=name, body=body)

def reindex(source, dest, query, update=True):
    es = settings.ES_CLIENT
    if update:
        # makes version consistent between indexes, updates doc if id already exists
        helpers.reindex(client=es, source_index=source, target_index=dest, query=query, version_type=external)    
    else:
        # version_type=internal dumps all documents, overwriting same ids. 
        helpers.reindex(client=es, source_index=source, target_index=dest, query=query, version_type=internal)    

def build_mortar_query(tree):
    # set base query
    query = {
        'query': {'match_all': {}},
        'filter': {
            'bool': {}
        }
    }   
    # get tree terms  
    terms = get_regex_list(tree)
    
    return query
