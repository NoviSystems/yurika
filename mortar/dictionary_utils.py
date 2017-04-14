import mortar.models as models
from django.conf import settings
from django.db import transaction
import urllib.request
import datetime
import simplejson, json
import os
import nltk

def update_dictionaries():
    dict_path = settings.DICTIONARIES_PATH
    all_dicts = models.AIDictionary.objects.all()
    for root, dirs, files in os.walk(dict_path):
        for f in files:
            if f.endswith(".txt"):
                filepath = os.sep.join([root, f])
                with open(filepath, "r") as dictfile:
                   name = dictfile.readline().strip('\n')
                   id = dictfile.readline().strip('\n')
                   words = dictfile.read().split('\n')
                   d,created = models.AIDictionary.objects.get_or_create( name=name, id=id, filepath=os.sep.join([root, f]) )
                   for word in words:
                       if len(word) > 0:
                           w,created = models.AIDictionaryObject.objects.get_or_create( word=word, dictionary=d )

def associate_tree(tree):
    categories = tree.categories.all()
    for node in categories:
        aidict = models.AIDictionary.objects.filter(name__iexact=node.name)
        if len(aidict) > 0:
            print(aidict[0].name)
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
  
def annotate_doc(esdoc, dicts):
     url = esdoc['_source']['url']
     tstamp = esdoc['_source']['tstamp'][:-1]
     dt_tstamp = datetime.datetime.strptime(tstamp, "%Y-%m-%dT%H:%M:%S.%f")
     doc,created = models.Document.objects.get_or_create(uri=url, crawled_at=dt_tstamp)
     content = esdoc['_source']['content']
     sentences = nltk.tokenize.sent_tokenize(content)
     tokens = [nltk.tokenize.word_tokenize(s) for s in sentences]
     print(tokens)
     

def annotate(tree):
    tree_dicts = get_tree_dictionaries(tree)
    dicts = get_dict_of_dicts(tree_dicts)
    docs = get_indexed_docs(tree)
    annotate_doc(docs[0], dicts)
     
#find . -size  0 -print0 |xargs -0 rm
#for f in *.csv; do sed -i -e '1iDOC_ID,ID\' $f; done; # brg
#for f in *.csv; do sed -i -e '1iID,VALUE\' $f; done; # csv 
# csvsql --db postgresql://vis:tiartrop@localhost:5432/portrait --insert --encoding utf-8 --delimiter \, --no-constraints --table date_facet --blanks date_facet.csv
