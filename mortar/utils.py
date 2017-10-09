# uncompyle6 version 2.12.0
# Python bytecode 3.5 (3351)
# Decompiled from: Python 2.7.13 (default, Jan 19 2017, 14:48:08) 
# [GCC 6.3.0 20170118]
# Embedded file name: /home/mejohn/itng/yurika/mortar/utils.py
# Compiled at: 2017-10-01 19:31:32
# Size of source mod 2**32: 9656 bytes
import os
import json
from xml.etree import ElementTree as etree
from pyparsing import nestedExpr
from django.conf import settings
import mortar.models as models

def get_json_tree(queryset, max_level=None):
    pk_attname = 'id'
    tree = []
    node_dict = dict()
    min_level = None
    for cat in queryset:
        if min_level is None:
            min_level = cat.level
        pk = getattr(cat, pk_attname)
        try:
            dict_id = cat.dictionary.id
        except:
            dict_id = None

        node_info = dict(label=cat.name, id=pk, regex=cat.regex, dictionary=dict_id)
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


def get_anno_json(tree):
    annos = models.Annotation.objects.filter(tree=tree)
    out = []
    num = 1
    for anno in annos:
        out.append([anno.id, anno.content, anno.document.url, anno.query.name, anno.score])
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


def create_query_part(qtype, qid, op, query):
    if not op:
        op = '+'
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
        for part in PARTS_OF_SPEECH:
            if part[0] == qid:
                name = part[1]

        part = models.PartOfSpeechPart.objects.create(query=query, part_of_speech=qid, op=op, name=name)
        return part


def update_dictionaries():
    dict_path = settings.DICTIONARIES_PATH
    for root, dirs, files in os.walk(dict_path):
        for f in files:
            if f.endswith('.txt') and os.path.getsize(os.sep.join([root, f])) > 1:
                filepath = os.sep.join([root, f])
                with open(filepath, 'rb+') as dictfile:
                    d, created = models.Dictionary.objects.get_or_create(name=f.split('.')[0], filepath=os.sep.join([root, f]))
                    for line in dictfile:
                        word = line.decode('utf-8').strip('\n')
                        w, created = models.Word.objects.get_or_create(name=word, dictionary=d)


def associate_tree(tree):
    categories = tree.nodes.all()
    for node in nodess:
        aidict = models.Dictionary.objects.filter(name__iexact=node.name)
        if len(aidict) > 0:
            node.dictionary = aidict[0]
            node.save()


def make_dict_query(dictionary):
    out = []
    for word in dictionary.words.all():
        out.append({'match': {'content': word.name}})

    return {'bool': {'should': out}}


def make_regex_query(regex):
    return {'bool': {'must': {'regexp': {'content': regex.regex}}}}


def make_pos_query(pos):
    return {'bool': {'must': {'match': {'tokens': '|' + pos}}}}


def create_query_from_string(string):
    nest = nestedExpr().parseString(string).asList()

    def recurse_nest(n):
        if type(n) == type([]):
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
        tstamp = esdoc['_source']['tstamp'][:-1]
        dt_tstamp = datetime.datetime.strptime(tstamp, '%Y-%m-%dT%H:%M:%S.%f')
        doc, created = models.Document.objects.get_or_create(url=url, crawled_at=dt_tstamp, projecttree=tree)
        return doc
    except Exception as e:
        return


def tokenize_doc(esdoc):
    content = esdoc['_source']['content']
    sentences = nltk.tokenize.sent_tokenize(content)
    tokens = [nltk.tokenize.word_tokenize(s) for s in sentences]
    return (
     sentences, tokens)


def pos_tokens(tokens):
    return nltk.pos_tag_sents(tokens)


def list_tree_patterns(tree):
    cats = models.Node.objects.filter(projecttree=tree)
    out = []
    for cat in cats:
        if cat.regex:
            out.append((cat.name, cat.regex))

    return out


def pos_tokens_to_es(content, tree):
    regexs = list_tree_patterns(tree)
    out = []
    place = 0
    for tupl in content:
        sent, pos = tupl
        body = {'_op_type': 'index',
         '_type': 'sentence',
         '_source': {}}
        body['_source']['content'] = sent
        body['_source']['place'] = place
        place += 1
        for name, regex in regexs:
            body['_source']['patterns'] = sent

        body['_source']['tokens'] = ''.join([' ' + i[0] + '|' + i[1] for i in pos if len(i[1]) and i[0] not in string.punctuation])
        out.append(body)

    return out


def get_indexed_docs(tree):
    es = settings.ES_CLIENT
    query = {'query': {'match_all': {}}}
    queried = es.search(index='filter_' + tree.slug, _source_include=[
     'content', 'url', 'tstamp'], body=query, size=10000)
    return queried['hits']['hits']


def insert_pos_record(slug, id, esdoc, content, tree):
    es = settings.ES_CLIENT
    body = {'url': esdoc['_source']['url'],
     'tstamp': esdoc['_source']['tstamp'][:-1]}
    es.index(index='pos_' + slug, id=id, doc_type='doc', body=json.dumps(body))
    sentences = pos_tokens_to_es(content, tree)
    for sentence in sentences:
        sentence['_index'] = 'pos_' + slug
        sentence['_parent'] = id

    helpers.bulk(client=es, actions=sentences)


def process(tree):
    docs = get_indexed_docs(tree)
    tree_has_regex = elastic_utils.create_pos_index(tree)
    for esdoc in docs:
        doc = clean_doc(esdoc, tree)
        if doc is not None:
            sentences, tokens = tokenize_doc(esdoc)
            pos = pos_tokens(tokens)
            content = list(zip(sentences, pos))
            insert_pos_record(tree.slug, doc.id, esdoc, content, tree)


def annotate(tree, category, query):
    if category == 'S':
        doc_type = 'sentence'
    else:
        if category == 'P':
            doc_type = 'paragraph'
        elif category == 'D':
            doc_type = 'doc'
        body = {'query': {'filtered': {'filter': json.loads(query.elastic_json)}
                   }
         }
        es = settings.ES_CLIENT
        search = es.search(index='pos_' + tree.slug, doc_type=doc_type, body=body, size=10000)['hits']
        if search['total']:
            for hit in search['hits']:
                doc = models.Document.objects.get(id=int(hit['_routing']))
                anno = models.Annotation.objects.create(content=hit['_source']['content'], tree=tree, query=query, document=doc, place=int(hit['_source']['place']), anno_type=category)
# okay decompiling utils.cpython-35.pyc
