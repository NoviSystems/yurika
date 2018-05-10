"""
BSD 3-Clause License

Copyright (c) 2018, North Carolina State University
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. The names "North Carolina State University", "NCSU" and any trade‐name,
   personal name, trademark, trade device, service mark, symbol, image, icon,
   or any abbreviation, contraction or simulation thereof owned by North
   Carolina State University must not be used to endorse or promoteproducts
   derived from this software without prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import json
import os
import string
from datetime import datetime
from xml.etree import ElementTree as etree

import nltk
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from elasticsearch import helpers
from elasticsearch.client import IndicesClient
from pyparsing import nestedExpr

from mortar import models


def get_json_tree(queryset, max_level=None):
    tree = []
    flat_tree = []
    node_dict = dict()
    min_level = None
    for node in queryset:
        if min_level is None:
            min_level = node.level
        pk = getattr(node, 'id')
        try:
            dict_id = node.dictionary.id
        except Exception:
            dict_id = None

        node_info = dict(label=node.name, id=pk, regex=node.regex, dictionary=dict_id)
        flat_tree.append(node_info)
        if node.level == min_level:
            tree.append(node_info)
        else:
            parent_id = node.parent_id
            parent_info = node_dict.get(parent_id)
            if parent_info:
                if 'children' not in parent_info:
                    parent_info['children'] = []
                parent_info['children'].append(node_info)
        node_dict[pk] = node_info
    return tree, flat_tree


def get_dict_json():
    dicts = models.Dictionary.objects.all()
    out = []
    for d in dicts:
        j = {'id': d.id,
             'name': d.name,
             'words': [w.strip() for w in d.words.split('\n')]}
        out.append(j)
    return out


def get_dict_list():
    dicts = models.Dictionary.objects.all()
    out = {}
    for d in dicts:
        out[d.id] = d.words
    return json.dumps(out)


def get_anno_json(tree):
    annos = models.Annotation.objects.filter(tree=tree)
    out = []
    num = 1
    for anno in annos:
        out.append([anno.id, anno.content, anno.document.url, anno.query.name])
        num += 1

    return out


def read_mindmap(tree, mmstring):
    root = etree.fromstring(mmstring)
    for child in root:
        name = child.attrib.get('TEXT')
        if len(name) > 0 and child.tag == 'node':
            node, created = models.Node.objects.get_or_create(name=name, tree_link=tree, parent=None)
            create_mm_children(child, node, tree)
        else:
            create_mm_children(child, None, tree)


def create_mm_children(xmlparent, nodeparent, tree):
    children = xmlparent.getchildren()
    for child in children:
        if child.tag == 'node':
            name = child.attrib.get('TEXT')
            node, created = models.Node.objects.get_or_create(name=name, tree_link=tree, parent=nodeparent)
            if len(child.getchildren()) > 0:
                create_mm_children(child, node, tree)


def copy_nodes(old_tree, new_tree):
        old_nodes = old_tree.nodes.all()
        old_roots = [n for n in old_nodes if n.is_root_node()]
        for root in old_roots:
            branch = root.get_descendants(include_self=True)
            for node in branch:
                parent = None
                if node.parent:
                    possibles = models.Node.objects.filter(tree_link=new_tree, name=node.parent.name)
                    parent = [p for p in possibles if p.full_path_name == node.parent.full_path_name]
                    parent = parent[0]
                with transaction.atomic():
                    new_node = models.Node.objects.create(
                        name=node.name,
                        parent=parent,
                        tree_link=new_tree,
                        regex=node.regex
                    )
                    new_node.save()


def create_query_part(qtype, qid, query, op=None):
    if not op:
        op = 1
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
        for part in settings.PARTS_OF_SPEECH:
            if part[0] == qid:
                name = part[1]

        part = models.PartOfSpeechPart.objects.create(query=query, part_of_speech=qid, op=op, name=name)
        return part


def update_dictionaries():
    es = settings.ES_CLIENT
    es_actions = []
    i_client = IndicesClient(client=es)
    if not i_client.exists('dictionaries'):
        i_client.create('dictionaries')
    # chunk_size = 2048
    # es_actions = []
    dict_path = settings.DICTIONARIES_PATH
    for root, dirs, files in os.walk(dict_path):
        for f in files:
            if f.endswith('.txt') and os.path.getsize(os.sep.join([root, f])) > 1:
                filepath = os.sep.join([root, f])
                with open(filepath, encoding='utf-8') as dictfile:
                    d, created = models.Dictionary.objects.get_or_create(
                        name=f.split('.')[0],
                        filepath=os.path.join(root, f),
                    )
                    d.words = dictfile.read()
                    words = d.words.split("\n")
                    if not words[-1]:
                        wordsNew = words[:-1]
                    else:
                        wordsNew = words[:]
                    d.save()
                    es_actions.append({
                        '_op_type': 'index',
                        '_type': 'dictionary',
                        '_id': d.id,
                        '_source': {
                            'name': d.name,
                            'words': wordsNew
                        },
                        '_index': 'dictionaries',
                    })
    helpers.bulk(client=es, actions=es_actions, max_retries=2, request_timeout=60)


# TODO
def write_to_new_dict(new_dict):
    pass


def associate_tree(tree):
    nodes = tree.nodes.all()
    for node in nodes:
        aidict = models.Dictionary.objects.filter(name__iexact=node.name)
        if len(aidict) > 0:
            node.dictionary = aidict[0]
            node.save()

def make_dict_query(dictionary):
     return {
            'terms': {
                'content': {
                    'index': 'dictionaries',
                    'type': 'dictionary',
                    'id': dictionary.dictionary_id,
                    'path': 'words',
                }
            }
        }

def make_regex_query(regex):
    return {'bool': {'must': {'regexp': {'content': regex.regex if regex.regex else regex.name}}}}


def make_pos_query(pos):
    return {'bool': {'must': {'match': {'tokens': '|' + pos}}}}


def make_tree_query(nodes):
    out = []
    for word in nodes['names']:
        out.append({'match': {'content': word}})
    for regex in nodes['regexs']:
        out.append({'regexp': {'content': regex}})
    return {'bool': {'should': out}}


def create_query_from_part(part_type, part):
    if part_type == 'dictionary':
        return json.dumps(make_dict_query(part.dictionary))
    elif part_type == 'regex':
        return json.dumps(make_regex_query(part.regex))
    elif part_type == 'part_of_speech':
        return json.dumps(make_pos_query(part.part_of_speech))
    else:
        return {}


def create_query_from_string(string):
    nest = nestedExpr().parseString(string).asList()

    def recurse_nest(n):
        if isinstance(n, list):
            return {'bool': {'should' if n[1] == '|' else 'must': [recurse_nest(n[0]), recurse_nest(n[2])]}}
        s = n.split('.')
        if s[0] == 'dictionary':
            return make_dict_query(models.Dictionary.objects.get(id=s[1]))
        if s[0] == 'regex':
            return make_regex_query(models.Node.objects.get(id=s[1]))
        if s[0] == 'part_of_speech':
            return make_pos_query(s[1])
        return json.loads(models.Query.objects.get(id=s[1]).elastic_json)

    dnest = json.dumps(recurse_nest(nest[0]))
    return dnest


def clean_doc(esdoc, tree):
    try:
        url = esdoc['_source']['url']
        tstamp = esdoc['_source']['tstamp']
        dt_tstamp = datetime.strptime(tstamp, '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=timezone.utc)
        doc, created = models.Document.objects.get_or_create(
            url=url,
            crawled_at=dt_tstamp,
            tree=tree,
            index=tree.doc_source_index,
        )
        return doc
    except Exception as e:
        print(e)


def tokenize_doc(esdoc):
    content = esdoc['_source']['content']
    sentences = nltk.tokenize.sent_tokenize(content)
    tokens = [nltk.tokenize.word_tokenize(s) for s in sentences]
    pos_tokens = nltk.pos_tag_sents(tokens)
    return list(zip(sentences, pos_tokens))


def tokenize_paragraph(paragraph):
    sentences = nltk.tokenize.sent_tokenize(paragraph)
    tokens = [nltk.tokenize.word_tokenize(s) for s in sentences]
    pos_tokens = nltk.pos_tag_sents(tokens)
    return list(zip(sentences, pos_tokens))


def pos_tokens(tokens):
    return nltk.pos_tag_sents(tokens)


def list_tree_patterns(tree):
    cats = models.Node.objects.filter(tree_link=tree)
    out = []
    for cat in cats:
        if cat.regex:
            out.append((cat.name, cat.regex))
    return out


def content_to_sentences(content, paragraph, tree, esdoc, django_id):
    # regexs = list_tree_patterns(tree)
    es_out = []
    tagged_paragraph = ''
    place = 0
    es = settings.ES_CLIENT
    for sent, pos in content:
        tagged_sentence = ''.join([
            ' ' + i[0] + '|' + i[1] for i in pos
            if len(i[1]) and i[0] not in string.punctuation
        ])
        body = {
           '_index' : tree.doc_dest_index.name,
           '_type': 'sentence',
           '_source': {
                'content': sent.rstrip('\n'),
               	'paragraph': paragraph,
               	'place': place,
                'tokens': tagged_sentence,
		'source_doc_id': django_id,
		'doc_content': content
            }
        }
        place += 1
        es_out.append(body)
        tagged_paragraph += tagged_sentence + ' '
    return tagged_paragraph, es_out


def content_to_paragraphs(esdoc, tree, django_id):
    content = esdoc['_source']['content']
    paragraphs = content.split('\n')
    out = []
    place = 0
    for p in paragraphs:
        if len(p.strip()):
            p = p.rstrip('\n')
            sentence_content = tokenize_paragraph(p)
            tags, sentences = content_to_sentences(sentence_content, place, tree, esdoc, django_id)
            out.extend(sentences)
            body = {
                '_index' : tree.doc_dest_index.name,
                '_type': 'paragraph',
                '_source': {
                    'content': p,
                    'tokens': tags,
                    'place': place,
		    'source_doc_id': django_id,
		    'doc_content': content
                }
            }
            out.append(body)
            place += 1
    return out


def get_indexed_docs(tree, filter_query):
    es = settings.ES_CLIENT
    query = {'query': {'match_all': {}}}
    if len(filter_query['names']) or len(filter_query['regexs']):
        query = {'query': make_tree_query(filter_query)}
    queried = helpers.scan(es, scroll=u'1h', raise_on_error=False, query=query, size=500, clear_scroll=False, index=tree.doc_source_index.name, doc_type='doc')
    return queried


def insert_pos_record(id, esdoc, tree, query):
    es = settings.ES_CLIENT
    body = {
#        'url': esdoc['_source']['url'],
        'tstamp': esdoc['_source']['tstamp'],
        'content': esdoc['_source']['content'],
    }
    es.index(index=tree.doc_dest_index.name, id=id, doc_type='doc', body=json.dumps(body))
    if query.category == 0:
        parag, es_out = content_to_sentences(tokenize_doc(esdoc), 0, tree, esdoc, id)
        helpers.bulk(client=es, actions=es_out, max_retries=2, request_timeout=60)
    elif query.category == 1:
        helpers.bulk(client=es, actions=content_to_paragraphs(esdoc, tree, id), max_retries=2, request_timeout=60)


def create_pos_index(tree):
    es = settings.ES_CLIENT
    i_client = IndicesClient(client=es)
    name = tree.doc_dest_index.name
    if not i_client.exists(name):

        pos_settings ={
            'settings': {
                    'number_of_shards': 5,
                    'number_of_replicas': 1,
                    'analysis': {
                           'analyzer': {
                                 'keyword_analyzer' : {
                                        'tokenizer':'keyword',
                                        'filter':['lowercase','minimal_english_stemmer'],
                                        'type' : 'custom'
                                  },
                                  'standard_analyzer':{
                                        'tokenizer':'standard',
                                        'filter':['lowercase','minimal_english_stemmer'],
                                        'type' : 'custom'
                                  },
                                  'edgeNgram_analyzer': {
                                        'type': 'custom',
                                        'tokenizer': 'standard',
                                        'filter': ['lowercase','edgeNgram_filter']
                                  }
                            },
                            'filter' : {
                                  'minimal_english_stemmer' : {
                                        'type' : 'stemmer',
                                        'name' : 'minimal_english'
                                  },
                                  'edgeNgram_filter' : {
                                        'type': 'edgeNGram',
                                        'min_gram': 2,
                                        'max_gram': 8
                                  }
                            }
                    }
            },
            'mappings': {
                    'doc': {
                           'properties': {
                                  'content': {
                                        'type' : 'text'
                                  },
                                  'tstamp': {
                                        'type': 'date',
                                        'format': 'strict_date_optional_time||epoch_millis'
                                  }
                           }
                    },

                    'sentence': {
                           'properties': {
                                  'tokens' : {
                                        'type' : 'text',
                                        'analyzer' : 'keyword'
                                  },
                                  'content' : {
                                        'fields' : {
                                              'raw' : {
                                                  'type' : 'text',
                                                  'analyzer' : 'keyword'
                                              },
                                              'keyword_tokenized' : {
                                                  'type' : 'text',
                                                  'analyzer' : 'keyword_analyzer'
                                              },
                                              'standard_tokenized' : {
                                                  'type' : 'text',
                                                  'analyzer' : 'standard_analyzer'
                                              },
                                              'ngram_tokenized' : {
                                                  'type' : 'text',
                                                  'analyzer' : 'edgeNgram_analyzer'
                                              }
                                        },
                                        'type' : 'text'
                                  },
                                  'source_doc_id' : {
                                        'type' : 'text',
                                        'analyzer' : 'keyword'
                                  },
                                  'doc_content' : {
                                        'type' : 'text',
                                        'analyzer' : 'keyword'
                                  }
                           }
                    },

                    'paragraph': {
                           'properties': {
                                  'tokens' : {
                                        'type' : 'text',
                                        'analyzer' : 'keyword'
                                  },
                                  'content' : {
                                        'fields' : {
                                              'raw' : {
                                                  'type' : 'text',
                                                  'analyzer' : 'keyword'
                                              },
                                              'keyword_tokenized' : {
                                                  'type' : 'text',
                                                  'analyzer' : 'keyword_analyzer'
                                              },
                                              'standard_tokenized' : {
                                                  'type' : 'text',
                                                  'analyzer' : 'standard_analyzer'
                                              },
                                              'ngram_tokenized' : {
                                                  'type' : 'text',
                                                  'analyzer' : 'edgeNgram_analyzer'
                                              }
                                        },
                                        'type' : 'text'
                                  },
                                  'source_doc_id' : {
                                        'type' : 'text',
                                        'analyzer' : 'keyword'
                                  },
                                  'doc_content' : {
                                        'type' : 'text',
                                        'analyzer' : 'keyword'
                                  }
                           }
                     }
               }
        }
     
        i_client.create(index=name, body=json.dumps(pos_settings))


def process(tree, filter, query):
    docs = get_indexed_docs(tree, filter)
    create_pos_index(tree)
    count = 1
    previous = 0
    for esdoc in docs:
        if count > previous:
            doc = clean_doc(esdoc, tree)
            if doc is not None:
                insert_pos_record(doc.id, esdoc, tree, query)
        count += 1

def fetch_terms_from_dictionary(name):
    es = settings.ES_CLIENT
    body = {"query": {"term" : {"name" : name}}}
    search = helpers.scan(es, query=body, size=500, index='dictionaries', doc_type = 'dictionary')
    for hit in search:
        words = hit['_source']['words']
        return words
            

def annotate(analysis):
    tree = analysis.mindmap
    query = analysis.query
    es = settings.ES_CLIENT
    i_client = IndicesClient(client=es)
    if not i_client.exists(tree.doc_dest_index.name):
        process(tree, {'names': [], 'regexs': []})
    doc_type = 'doc'
    if query.category == 0:
        doc_type = 'sentence'
    elif query.category == 1:
        doc_type = 'paragraph'
    else:
        doc_type = 'doc'
    body = {'query': json.loads(query.elastic_json)}
    search = helpers.scan(es, scroll=u'1h', query=body, raise_on_error=False, size=500, clear_scroll=False, index=tree.doc_dest_index.name, doc_type=doc_type)
    for hit in search:
        doc = models.Document.objects.get(id=int(hit['_source']['source_doc_id']) if doc_type != 'doc' else int(hit['_id']))
        with transaction.atomic():
            models.Annotation.objects \
                .using('explorer') \
                .create(
                    content=hit['_source']['content'],
                    analysis_id=analysis.id,
                    query_id=query.id,
                    document_id=doc.id,
                    url=doc.url,
                    category=query.category)
