from django.contrib import admin
from django_mptt_admin.admin import FilterableDjangoMpttAdmin
from .models import Project, ProjectTree, Category, AIDictionary, AIDictionaryObject, Document, Annotation, QueryLog

class CategoryAdmin(FilterableDjangoMpttAdmin):
    list_filter = ('projecttree',)

admin.site.register(Project)
admin.site.register(ProjectTree)
admin.site.register(Category, CategoryAdmin)
admin.site.register(AIDictionary)
admin.site.register(AIDictionaryObject)
admin.site.register(Document)
admin.site.register(Annotation)
admin.site.register(QueryLog)
