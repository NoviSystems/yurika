from django.contrib import admin
from django_mptt_admin.admin import FilterableDjangoMpttAdmin
from .models import Project, ProjectTree, Category, AIDictionary, AIDictionaryObject, Document, Annotation, TermVector, Query, QueryPart, DictionaryPart, RegexPart, SubQueryPart, PartOfSpeechPart

class CategoryAdmin(FilterableDjangoMpttAdmin):
    list_filter = ('projecttree',)

admin.site.register(Project)
admin.site.register(ProjectTree)
admin.site.register(Category, CategoryAdmin)
admin.site.register(AIDictionary)
admin.site.register(AIDictionaryObject)
admin.site.register(Document)
admin.site.register(Annotation)
admin.site.register(TermVector)
admin.site.register(Query)
admin.site.register(QueryPart)
admin.site.register(DictionaryPart)
admin.site.register(RegexPart)
admin.site.register(SubQueryPart)
admin.site.register(PartOfSpeechPart)
