from .models import ProjectTree, Category
from django.conf import settings
import urllib.request
import simplejson, json

from elasticsearch.client import IndicesClient
from elasticsearch import helpers

from .tree_utils import get_regex_list

def create_index(name, analysis_conf=None):
    es = settings.ES_CLIENT
    i_client = IndicesClient(client=es)

    if i_client.exists(name):
        i_client.delete(name)

    if analysis_conf:
        body = analysis_conf
    else:
        body = create_analyzer_conf()
    i_client.create(index=name, body=body)

def reindex(source, dest, query, update=True):
    es = settings.ES_CLIENT
    if update:
        # makes version consistent between indexes, updates doc if id already exists
        helpers.reindex(client=es, source_index=source, target_index=dest, query=query)    
    else:
        # version_type=internal dumps all documents, overwriting same ids. 
        helpers.reindex(client=es, source_index=source, target_index=dest, query=query)    

def build_mortar_query(terms):
    # get tree terms  
    #terms = get_regex_list(tree)
    to_query = []
    for term in terms:
       to_query.append(
           { "match": {
               "content": term  
             }
           }
       )
    query = { 
        'query': {
            'bool': {
                'must': to_query
            }   
        }   
    }
    return query 

def create_analyzer_conf():
    # hardcode some analyzers for now
    return {
        "settings" : {
          "analysis": {
            "analyzer": {
              "content" : {
                "type": "pattern",
                "pattern": "\\s+",
                "filter": ["lowercase"]
                
              }
            }
          }
        }
    }
