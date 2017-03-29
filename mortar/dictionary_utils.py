from .models import ProjectTree, Category, AIDictionary, AIDictionaryObject
from django.conf import settings
import urllib.request
import simplejson, json

def update_dictionaries():
    dict_path = settings.DICTIONARIES_PATH
    

def associate_tree(tree):
    pass

def build_analyzer_conf(tree):
    pass
