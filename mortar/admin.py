from django.contrib import admin
from mortar import models
from django_mptt_admin.admin import FilterableDjangoMpttAdmin

class NodeAdmin(FilterableDjangoMpttAdmin):
    list_filter = ('tree_link', )

admin.site.register(models.Node, NodeAdmin)
admin.site.register(models.Tree)
admin.site.register(models.Document)
admin.site.register(models.Dictionary)
admin.site.register(models.Annotation)
admin.site.register(models.Query)
admin.site.register(models.QueryPart)
admin.site.register(models.SubQueryPart)
admin.site.register(models.DictionaryPart)
admin.site.register(models.RegexPart)
admin.site.register(models.PartOfSpeechPart)
admin.site.register(models.Crawler)
admin.site.register(models.URLSeed)
admin.site.register(models.FileSeed)
admin.site.register(models.ElasticIndex)
admin.site.register(models.Analysis)
