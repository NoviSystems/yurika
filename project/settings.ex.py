'''
-*- Development Settings -*-

This file contains development-specific settings. You can run the django
development server without making any changes to this file, but it's not
suitable for production. The production settings files are located under
the './deploy' directory.
'''

from .common_settings import *
from elasticsearch import Elasticsearch, RequestsHttpConnection

# Set your MEDIA_ROOT to a directory that does not already exist.
MEDIA_ROOT = path('files')

PARTS_OF_SPEECH = (('CC', 'Coordinating Conjunction'),
                   ('CD', 'Cardinal Number'),
                   ('DT', 'Determiner'),
                   ('EX', 'Existential there'),
                   ('FW', 'Foreign Word'),
                   ('IN', 'Preposition of subordinating conjunction'),
                   ('JJ', 'Adjective'),
                   ('JJR', 'Adjective, comparitive'),
                   ('JJS', 'Adjective, superlative'),
                   ('LS', 'List item marker'),
                   ('MD', 'Modal'),
                   ('NN', 'Noun, singular or mass'),
                   ('NNS', 'Noun, plural'),
                   ('NNP', 'Proper Noun, singular'),
                   ('NNPS', 'Proper Noun, plural'),
                   ('PDT', 'Predeterminer'),
                   ('POS', 'Possessive ending'),
                   ('PRP', 'Personal pronoun'),
                   ('PRP$', 'Possessive pronoun'),
                   ('RB', 'Adverb'),
                   ('RBR', 'Adverb, comparative'),
                   ('RBS', 'Adverb, superlative'),
                   ('RP', 'Particle'),
                   ('SYM', 'Symbol'),
                   ('TO', 'to'),
                   ('UH', 'Interjection'),
                   ('VB', 'Verb, base form'),
                   ('VBD', 'Verb, past tense'),
                   ('VBG', 'Verb, gerund or present participle'),
                   ('VBN', 'Verb, past participle'),
                   ('VBP', 'Verb, non-3rd person singular present'),
                   ('VBZ', 'Verb 3rd person singular present'),
                   ('WDT', 'Wh-determiner'),
                   ('WP', 'Wh-pronoun'),
                   ('WP$', 'Possessive wh-pronoun'),
                   ('WRB', 'Wh-adverb')) 

ES_URL = 'http://10.36.1.1:9200/'
ES_CLIENT = Elasticsearch([ES_URL], connection_class=RequestsHttpConnection)
DICTIONARIES_PATH = 'dictionaries/'
