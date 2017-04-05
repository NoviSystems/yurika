from .models import ProjectTree, Category, AIDictionary, AIDictionaryObject
from django.conf import settings
from django.db import transaction
import urllib.request
import simplejson, json


from .tree_utils import get_regex_list
 
def update_dictionaries():
    dict_path = settings.DICTIONARIES_PATH
    

def associate_tree(tree):
    terms = tree.categories.all()
    for node in terms:
        aidict = AIDictionary.objects.filter(name=node.name)
        if len(aidict) > 0:
            for word in aidict.words.all():
                with transaction.atomic():
                    new_node = Category.objects.get_or_create(
                        name=word,
                        parent=node
                        projecttree=tree
                        is_rule=False
                    )
                    new_node.save()
            
def build_analyzer_conf(tree):
    pass
