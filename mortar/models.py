from django.db import models
from django.conf import settings
from mptt.models import MPTTModel, TreeForeignKey

# http://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
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
class Project(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    assigned = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="projects")

    def __str__(self):
        return "Project: %s" % self.name

class ProjectTree(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    project = models.ForeignKey(Project, related_name="trees")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="owned_trees")
    editors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="editor_trees")

    def __str__(self):
        return "Tree: %s" % self.name

    class Meta:
        verbose_name = "Tree"
        verbose_name_plural = "Trees"

class AIDictionary(models.Model):
    # id 
    name = models.CharField(max_length=50)
    filepath = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Dictionary"
        verbose_name_plural = "Dictionaries"
        
class AIDictionaryObject(models.Model):
    word = models.CharField(max_length=255)
    dictionary = models.ForeignKey(AIDictionary, related_name="words")

    def __str__(self):
        return self.word

    class Meta:
        verbose_name = "Word"
        verbose_name_plural = "Words"

class Category(MPTTModel):
    name = models.CharField(max_length=50)
    regex = models.CharField(max_length=255, null=True, blank=True)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True)
    projecttree = models.ForeignKey(ProjectTree, related_name="categories")
    dictionary = models.ForeignKey(AIDictionary, null=True, blank=True, related_name="categories")

    @property
    def full_path_name(self):
        ancestors = self.get_ancestors()
        path = ''
        for ancestor in ancestors:
            if len(path) == 0:
                path = ancestor.name
            else:
                path = path + '.' +  ancestor.name
        return path

    @property
    def has_dictionary(self):
        return self.dictionary is not None

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

    class MPTTMeta:
        order_insertion_by = ['name']

class Document(models.Model):
    url = models.URLField()
    crawled_at = models.DateTimeField()
    projecttree = models.ForeignKey('ProjectTree', related_name="documents")

    def __str__(self):
        return self.url

class TermVector(models.Model):
    term = models.CharField(max_length=255)
    matched = models.CharField(max_length=255)
    document = models.ForeignKey('Document', related_name="found_terms")
    position = models.IntegerField(default=0)
    start_offset = models.IntegerField(default=0)
    end_offset = models.IntegerField(default=0)

class Annotation(models.Model):
    content = models.TextField()
    score = models.FloatField(default=0)
    projecttree = models.ForeignKey('ProjectTree', related_name="annotations")
    words = models.ManyToManyField('AIDictionaryObject', blank=True, related_name="annotations")
    regexs = models.ManyToManyField('Category', blank=True, related_name="annotations")
    termvectors = models.ManyToManyField('TermVector', blank=True, related_name="annotations")
    anno_type = models.CharField(max_length=1, choices=(('S', 'Sentence'),('P', 'Paragraph')))

    def __str__(self):
        return str(self.id)

class Query(models.Model):
    name = models.CharField(max_length=30, blank=True)
    elastic_json = models.TextField(blank=True)
    def __str__(self):
        return name

class QueryPart(models.Model):
    query = models.ForeignKey('Query', related_name="parts")
    op = models.CharField(max_length=1, choices=(('+', 'AND'), ('|', 'OR')))
    name = models.CharField(max_length=30)
    def __str__(self):
        return "QueryPart: %d" % self.id
    
class DictionaryPart(QueryPart):
    dictionary = models.ForeignKey('AIDictionary', related_name="dictionaries")
    
class RegexPart(QueryPart):
    regex = models.ForeignKey('Category', related_name="regexs")
    
class SubQueryPart(QueryPart):
    subquery = models.ForeignKey('Query', related_name="subqueries")
