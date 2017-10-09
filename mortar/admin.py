# uncompyle6 version 2.12.0
# Python bytecode 3.5 (3351)
# Decompiled from: Python 2.7.13 (default, Jan 19 2017, 14:48:08) 
# [GCC 6.3.0 20170118]
# Embedded file name: /home/mejohn/itng/yurika/mortar/admin.py
# Compiled at: 2017-09-30 10:16:55
# Size of source mod 2**32: 844 bytes
from django.contrib import admin
from mortar import models
from django_mptt_admin.admin import FilterableDjangoMpttAdmin

class NodeAdmin(FilterableDjangoMpttAdmin):
    list_filter = ('tree_link', )


admin.site.register(models.Node, NodeAdmin)
admin.site.register(models.Tree)
admin.site.register(models.Document)
admin.site.register(models.Dictionary)
admin.site.register(models.Word)
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
# okay decompiling admin.cpython-35.pyc
