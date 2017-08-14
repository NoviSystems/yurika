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
                with open(filepath, "rb+") as dictfile:
                    d,created = models.AIDictionary.objects.get_or_create(name=f.split('.')[0], filepath=os.sep.join([root, f]) )
                    print(d.name)
                    for line in dictfile:
                        word = line.decode("utf-8").strip('\n')
                        w,created = models.AIDictionaryObject.objects.get_or_create( word=word, dictionary=d )

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
     return (sentences,tokens)

def pos_tokens(tokens):
     return nltk.pos_tag_sents(tokens)

def dict_annotate(pos_tokens, dicts, tree, doc):
     for d in dicts:
         for obj in d.words.all():
             created = [ models.Annotation.objects.get_or_create(document=doc, content="".join([" "+i[0] if not i[0].startswith("'") and i[0] not in string.punctuation else i[0] for i in s]).strip(), anno_type='S', projecttree=tree) for s in pos_tokens for token in s if token[0]==obj.word ]
             for c in created:
                 c.words.add(obj)
                 c.save()

def regex_annotate(pos_tokens, tree, doc):
    for cat in tree.categories.all():
        regex = re.compile(cat.regex if cat.regex else cat.name)
        created = [ models.Annotation.objects.get_or_create(document=doc, content="".join([" "+i[0] if not i[0].startswith("'") and i[0] not in string.punctuation else i[0] for i in s]).strip(), anno_type='S', projecttree=tree) for s in pos_tokens for token in s if regex.fullmatch(token[0])]
        for c in created:
            c.regexs.add(cat)

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
    tree_has_regex = elastic_utils.create_pos_index(tree)
    for esdoc in docs:
        doc = clean_doc(esdoc, tree)
        if doc is not None:
            sentences, tokens = tokenize_doc(esdoc)
            pos = pos_tokens(tokens)
            content = list(zip(sentences, pos))
            elastic_utils.insert_pos_record(tree.slug, doc.id, esdoc, content, tree)

def annotate_by_termvector(tree, annotype, dictionaries, andor, regexs):
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
        for doc in termvectors['docs']:
            parent = [s['_routing'] for s in sentences if s['_id'] == doc['_id']]
            make_annos_from_tokens(doc, parent[0], dictionaries, andor, regexs, tree)

def make_annos_from_tokens(term_doc, parent, dictionaries, andor, regexs, tree):
    es = settings.ES_CLIENT
    esdoc = es.get(index='pos_' + tree.slug, doc_type="sentence", id=term_doc['_id'], parent=parent)    
    doc = models.Document.objects.get(id=int(parent))
    anno = models.Annotation.objects.create(content=esdoc['_source']['content'], projecttree=tree, anno_type="S")

    # create termvectors
    words = models.AIDictionaryObject.objects.filter(dictionary__in=dictionaries)
    words_matched = []
    cats_matched = []
    terms_created = []
    matched = False
    all_terms = term_doc['term_vectors']['content']['terms']
    for word in words:
        multi = word.word.lower().split(' ')
        chains = token_chains(multi, all_terms)
        for chain in chains:
            for token in chain:
                index = chain.index(token)
                t = models.TermVector.objects.create(term=multi[index], matched=word.word, document=doc, position=token['position'], start_offset=token['start_offset'], end_offset=token['end_offset'])
                terms_created.append(t)
                if word not in words_matched:
                    words_matched.append(word)

        #else:
        #    for term in all_terms:
        #@        if term == word.word:
        #            words_matched.append(word)
        #            for token in all_terms[term]['tokens']:
        #                t = models.TermVector.objects.create(term=term, matched=word.word, document=doc, position=token['position'], start_offset=token['start_offset'], end_offset=token['end_offset'])
        #                terms_created.append(t)


    for regex in regexs:
        for term in all_terms:        
            r = regex.regex
            pattern = re.compile(r)
            result = pattern.search(term)
            if result:
                cats_matched.append(regex)
                for token in term_doc['term_vectors']['content']['terms'][term]['tokens']:
                    t = models.TermVector.objects.create(term=term, matched=r, document=doc, position=token['position'], start_offset=token['start_offset'], end_offset=token['end_offset'])
                    terms_created.append(t)

    # update anno object
    anno.words.set(words_matched)
    anno.regexs.set(cats_matched)
    anno.termvectors.set(terms_created)

def token_chain(current_token, remaining_terms, term_tokens):
    if not remaining_terms:
        return [current_token]

    next_term = remaining_terms[0] 
    next_pos = current_token['position'] + 1
   
 
    if next_term not in term_tokens:
        return

    for token in term_tokens[next_term]['tokens']:
        if token['position'] == next_pos:
            sub_chain = token_chain(token, remaining_terms[1:], term_tokens)
            return None if sub_chain is None else [current_token] + sub_chain

def token_chains(terms, term_tokens):
    chains = []

    #import pdb; pdb.set_trace()
    if terms[0] not in term_tokens:
        return []

    for token in term_tokens[terms[0]]['tokens']:
        chain = token_chain(token, terms[1:], term_tokens)
        if chain is not None:
            chains.append(chain)
    return chains

def annotate_by_tree(tree, pos):
    tree_dicts = get_tree_dictionaries(tree)
    for doc in docs:
        dict_annotate(pos, tree_dicts, tree, doc)
        regex_annotate(pos, tree, doc)

def annotate_by_query(tree, query):
    body = { "query" : {
       "filtered": {
         "filter": json.loads(query.elastic_json)
       }
    }}
    es = settings.ES_CLIENT
    search = es.search(index="pos_" + tree.slug, doc_type="sentence", body=body, size=10000)['hits']
    if search['total']:
        for hit in search['hits']:
            doc = models.Document.objects.get(id=int(hit['_routing']))
            anno = models.Annotation.objects.create(content=hit['_source']['content'], projecttree=tree, query=query, document=doc, place=int(hit['_source']['place']),anno_type="S")
            
#find . -size  0 -print0 |xargs -0 rm
#for f in *.csv; do sed -i -e '1iDOC_ID,ID\' $f; done; # brg
#for f in *.csv; do sed -i -e '1iID,VALUE\' $f; done; # csv 
# csvsql --db postgresql://vis:tiartrop@localhost:5432/portrait --insert --encoding utf-8 --delimiter \, --no-constraints --table date_facet --blanks date_facet.csv
