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

    def __str__(self):
        return self.uri

class Annotation(models.Model):
    document = models.ForeignKey('Document', related_name="annotations")
    content = models.TextField()
    begin = models.IntegerField(default=0)
    end = models.IntegerField(default=0)
    score = models.FloatField(default=0)
    rule = models.CharField(max_length=255)
    projecttree = models.ForeignKey('ProjectTree', related_name="annotations")
    dictionary = models.ForeignKey('AIDictionary', blank=True, null=True, related_name="annotations")
    regex = models.ForeignKey('Category', blank=True, null=True, related_name="annotations")
    anno_type = models.CharField(max_length=1, choices=(('S', 'Sentence'),('P', 'Paragraph')))
    pos = models.CharField(max_length=5, choices=PARTS_OF_SPEECH)

    def __str__(self):
        return str(self.id)

class QueryLog(models.Model):
    annotation = models.ForeignKey('Annotation', related_name="queries")
    es_body = models.TextField()

    class Meta:
        verbose_name_plural = "Queries"
