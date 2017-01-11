from django.contrib import admin
from django_mptt_admin.admin import FilterableDjangoMpttAdmin
from .models import Project, ProjectTree, Category

class CategoryAdmin(FilterableDjangoMpttAdmin):
    list_filter = ('projecttree',)

admin.site.register(Project)
admin.site.register(ProjectTree)
admin.site.register(Category, CategoryAdmin)
