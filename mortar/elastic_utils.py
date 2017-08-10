from .models import ProjectTree, Category, AIDictionary, Query
from django.conf import settings
import urllib.request
import simplejson, json
import string
from elasticsearch.client import IndicesClient
from elasticsearch import helpers
from pyparsing import nestedExpr

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

def list_tree_patterns(tree):
    cats = Category.objects.filter(projecttree=tree)
    out = []
    for cat in cats:
        if cat.regex: 
            out.append((cat.name,cat.regex)) 
    return out

def create_pos_index(tree):
    i_client = IndicesClient(client=settings.ES_CLIENT)
    i_name = "pos_" + tree.slug
    if i_client.exists(i_name):
        i_client.delete(index=i_name)
    i_settings = {
      'settings': {
        'analysis': {
          'tokenizer': {},
          'filter': {},
          'analyzer': {
            'payloads': {
              'type': 'custom',
              'tokenizer': 'whitespace',
              'filter': [
                'lowercase',
                {'delimited_payload_filter': {
                  'encoding': 'identity'
                }}
              ]
            },
            'fulltext': {
              'type': 'custom',
              'stopwords': '_english_',
              'tokenizer': 'whitespace',
              'filter': [
                'lowercase',
                'type_as_payload'
              ]
            },
          }
        }
      },
      'mappings': {
        'doc': {
          'properties': {
            'url': {'type': 'string', 'index': 'not_analyzed'},
            'tstamp': {'type': 'date', 'format': 'strict_date_optional_time||epoch_millis'},
          }
        },
        'sentence': {
          '_parent': { 'type': 'doc' },
          'properties': {
            'content': {'type': 'string', 'analyzer': 'fulltext', "term_vector": "with_positions_offsets_payloads"},
            'tokens': {'type': 'string', 'analyzer': 'payloads', "term_vector": "with_positions_offsets_payloads"},
          }
        },
        'paragraph': {
          '_parent': { 'type': 'doc' },
          'properties': {
            'content': {'type': 'string', 'analyzer': 'fulltext', "term_vector": "with_positions_offsets_payloads"},
            'tokens': {'type': 'string', 'analyzer': 'payloads', "term_vector": "with_positions_offsets_payloads"},
          }
        }
      }
    }
    regexs = list_tree_patterns(tree)
    if len(regexs):
        #for name,regex in regexs:
            #i_settings['settings']['analysis']['tokenizer'][name] = {
            #        'type': 'pattern',
            #        'pattern': regex,
            #        'group': '0'                                            
            #}
        i_settings['settings']['analysis']['filter']['patterns'] = {
            'type': 'pattern_capture',
            'preserve_original': 1,
            'patterns': [r for n,r in regexs]
        }
        i_settings['settings']['analysis']['analyzer']['patterns'] = {
            'tokenizer': 'whitespace',
            'type': 'custom',
            'filter': [ 'lowercase' ]
        }
        i_settings['mappings']['sentence']['properties']['patterns'] = {'type': 'string', 'analyzer': 'patterns', 'term_vector': 'with_positions_offsets_payloads'}
        #i_settings['mappings']['paragraph']['properties'][name + '_pattern'] = {'type': 'string', 'analyzer': name, 'term_vector': 'with_positions_offsets_payloads'} 
        i_client.create(index=i_name, body=json.dumps(i_settings))
        return True
    i_client.create(index=i_name, body=json.dumps(i_settings))
    return False


def pos_tokens_to_es(content, tree):
    regexs = list_tree_patterns(tree)
    out = []
    for tupl in content:
        sent, pos = tupl
        body = {
            '_op_type': 'index',
            '_type': 'sentence',
            '_source': {}
        }
        body['_source']['content'] = sent
        for name,regex in regexs:
            body['_source']['patterns'] = sent
        body['_source']['tokens'] = "".join([" "+i[0]+"|"+i[1] for i in pos if len(i[1]) and i[0] not in string.punctuation])
        out.append(body)
    return out

def insert_pos_record(slug, id, esdoc, content, tree):
    es = settings.ES_CLIENT
    body = {
      'url': esdoc['_source']['url'],
      'tstamp': esdoc['_source']['tstamp'][:-1],
    }
    es.index(index='pos_' + slug, id=id, doc_type="doc", body=json.dumps(body))
    sentences = pos_tokens_to_es(content, tree)
    for sentence in sentences:
        sentence['_index'] = 'pos_' + slug
        sentence['_parent'] = id
    helpers.bulk(client=es, actions=sentences)
    #es.index(index='pos_' + slug, parent=id, doc_type="sentence", body=json.dumps(sentence))

def build_es_annotations(tree):
    docs = models.Document.objects.filter(projecttree=tree)
   
def make_dict_query(dictionary):
    out = []
    for word in dictionary.words.all():
        out.append({'match': {'content': word.word}})
    return { 'bool': {'should': out}}

def make_regex_query(regex):
    return {'bool': {'must': {'regexp': {'content': regex.regex}}}}

def make_pos_query(pos):
    return {'bool': {'must': {'match': {'tokens': '|' + pos }}}}

def create_query_from_string(string):
    nest = nestedExpr().parseString(string).asList()
    
    # [['regex.1', '+', 'dictionary.2'], '|', [['dictionary.4', '|', 'dictionary.10'], '+', 'regex.5']]
    # { | : [{ + : [regex.1, dictionary.2]}, { + : [ { | : [dictionary.4, dictionary.10] }, regex.5 ]} ]}
    
    def recurse_nest(n):
        if type(n) == type([]):
            return {'bool': { 'should' if n[1] == '|' else 'must' : [recurse_nest(n[0]), recurse_nest(n[2])] }}
        else:
            s = n.split('.')
            if s[0] == 'dictionary':
                return make_dict_query(AIDictionary.objects.get(id=s[1]))
            elif s[0] == 'regex':
                return make_regex_query(Category.objects.get(id=s[1]))
            elif s[0] == 'part_of_speech':
                return make_pos_query(s[1])
            else:
                return json.loads(Query.objects.get(id=s[1]).elastic_json)
    
    dnest = json.dumps(recurse_nest(nest[0]))
    print(dnest)
    return dnest
    
    
