from django.db import models
from django.conf import settings
from mptt.models import MPTTModel, TreeForeignKey

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

class Category(MPTTModel):
    name = models.CharField(max_length=50)
    is_rule = models.BooleanField(default=False)
    regex = models.CharField(max_length=255, null=True, blank=True)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True)
    projecttree = models.ForeignKey(ProjectTree, related_name="categories")

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

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

    class MPTTMeta:
        order_insertion_by = ['name']

class AIDictionary(models.Model):
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
