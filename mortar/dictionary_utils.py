import mortar.models as models
from django.conf import settings
from django.db import transaction
import urllib.request
import datetime
import simplejson, json
import os
import re, string
import nltk
import mortar.elastic_utils as elastic_utils

def update_dictionaries():
    dict_path = settings.DICTIONARIES_PATH
    for root, dirs, files in os.walk(dict_path):
        for f in files:
            if f.endswith(".txt") and os.path.getsize(os.sep.join([root, f])) > 1:
                filepath = os.sep.join([root, f])
                with open(filepath, "r+") as dictfile:
                    with transaction.atomic():
                        d,created = models.AIDictionary.objects.get_or_create(name=f.split('.')[0], filepath=os.sep.join([root, f]) )
                        print(d.name)
                        for line in dictfile:
                            word = dictfile.readline().strip('\n')
                            w = models.AIDictionaryObject.objects.create( word=word, dictionary=d )

def associate_tree(tree):
    categories = tree.categories.all()
    for node in categories:
        aidict = models.AIDictionary.objects.filter(name__iexact=node.name)
        if len(aidict) > 0:
            node.dictionary = aidict[0]
            node.save()

def get_tree_dictionaries(tree):
    # this probably won't work.
    dicts = models.AIDictionary.objects.filter(categories__projecttree=tree)
    return dicts

def get_dict_of_dicts(dicts):
    out = {}
    for d in dicts:
        words = []
        for w in d.words.all():
            words.append(w.word)
        out[d.name] = words
    return out

### THIS WON'T SCALE > 10000 DOCS. PLS FIX WHEN POSSIBLE ###
def get_indexed_docs(tree):
    es = settings.ES_CLIENT
    query = {
        'query': { 'match_all': {}}
    }
    queried = es.search(index="filter_"+tree.slug, 
                        _source_include=['content', 'url', 'tstamp'],
                        body=query,
                        size=10000
              )
    return queried['hits']['hits'] 
 
# UTA STEPS 
#  Tokenize (either sentence or paragraph)
#  Part of Speech
#  Dictionary Annotations
#  N-Gram
#    Distance Relationship

def clean_doc(esdoc, tree):
    try:
        url = esdoc['_source']['url']
        tstamp = esdoc['_source']['tstamp'][:-1]
        dt_tstamp = datetime.datetime.strptime(tstamp, "%Y-%m-%dT%H:%M:%S.%f")
        doc,created = models.Document.objects.get_or_create(url=url, crawled_at=dt_tstamp, projecttree=tree)
        return doc
    except Exception as e:
        return None

def tokenize_doc(esdoc, paragraph=False): 
     content = esdoc['_source']['content']
     if paragraph:
         # figure out paragraph stuff
         return None
     sentences = nltk.tokenize.sent_tokenize(content)
     tokens = [nltk.tokenize.word_tokenize(s) for s in sentences]
     return tokens

def pos_tokens(tokens):
     return nltk.pos_tag_sents(tokens)

def dict_annotate(pos_tokens, dicts, tree, doc):
     for d in dicts:
         for obj in d.words.all():
             [ models.Annotation.objects.get_or_create(dictionary=d, document=doc, rule=obj.word, pos=token[1], content="".join([" "+i[0] if not i[0].startswith("'") and i[0] not in string.punctuation else i[0] for i in s]).strip(), anno_type='S', projecttree=tree) for s in pos_tokens for token in s if token[0]==obj.word ]

def regex_annotate(pos_tokens, tree, doc):
    for cat in tree.categories.all():
        regex = re.compile(cat.regex if cat.regex else cat.name)
        [ models.Annotation.objects.get_or_create(regex=cat, document=doc, rule=cat.name, pos=token[1], content="".join([" "+i[0] if not i[0].startswith("'") and i[0] not in string.punctuation else i[0] for i in s]).strip(), anno_type='S', projecttree=tree) for s in pos_tokens for token in s if regex.fullmatch(token[0])]

def ngram():
    pass

def distance():
    pass

def frequencies(tree):
    # this feels way too easy, but it works?
    words = models.AIDictionaryObject.objects.filter(dictionary__categories__projecttree=tree)
    out = {}
    for word in words:
        out[word.word] = len(models.Annotation.objects.filter(words__word=word, projecttree=tree))
    return out

def process(tree):
    docs = get_indexed_docs(tree)
    elastic_utils.create_pos_index(tree.slug)
    for esdoc in docs:
        doc = clean_doc(esdoc, tree)
        if doc is not None:
            tokens = tokenize_doc(esdoc)
            pos = pos_tokens(tokens)
            elastic_utils.insert_pos_record(tree.slug, doc.id, esdoc, pos)

def annotate_by_query(tree, annotype, dictionaries, andor, regexs):
    query = make_query(dictionaries, andor, regexs)
    body = { "query" : {
        "filtered": {
         "filter": query
        }
    }}
    es = settings.ES_CLIENT

    if annotype == 'P':
        search = es.search(index="pos_" + tree.slug, doc_type="paragraph", body=body, size=10000)['hits']
    else:
        search = es.search(index="pos_" + tree.slug, doc_type="sentence", body=body, size=10000)['hits']

    if search['total']:
        sentences = []
        for hit in search['hits']:
          sentences.append({'_id': hit['_id'], '_routing': hit['_routing']})
        body = { 'docs': sentences }
        termvectors = es.mtermvectors(index='pos_' + tree.slug, doc_type="sentence", body=json.dumps(body), fields=['content']) 
        print(len(termvectors['docs']))

def make_query(dictionaries, andor, regexs):
    dicts = { 'bool': {'must': [] }}
    for d in dictionaries:
        dicts['bool']['must'].append({"bool": {"should":  or_dictionary(d)}} )

    regs = { 'bool': {'must': [] }}
    for r in regexs:
        regs['bool']['must'].append({"match": {"content": r.regex if r.regex is not None else r.name }}
)

    out = {}
    q = []
    if len(dicts['bool']['must']):
        q.append(dicts)
    if len(regs['bool']['must']):
        q.append(regs)
   
    if andor == 'or':
        out = { 'bool': {'should': q }}
    if andor == 'and': 
        out = { 'bool': { 'must': q }}
    else:
        out = q[0]

    return out

def or_dictionary(dictionary):
    out = []
    for word in dictionary.words.all():
        out.append({"match": {"content": word.word}})
    return out
 
def annotate_by_tree(tree, pos):
    tree_dicts = get_tree_dictionaries(tree)
    for doc in docs:
        dict_annotate(pos, tree_dicts, tree, doc)
        regex_annotate(pos, tree, doc)
    
#find . -size  0 -print0 |xargs -0 rm
#for f in *.csv; do sed -i -e '1iDOC_ID,ID\' $f; done; # brg
#for f in *.csv; do sed -i -e '1iID,VALUE\' $f; done; # csv 
# csvsql --db postgresql://vis:tiartrop@localhost:5432/portrait --insert --encoding utf-8 --delimiter \, --no-constraints --table date_facet --blanks date_facet.csv
