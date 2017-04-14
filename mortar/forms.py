from django import forms
from django.utils.text import slugify
from .models import ProjectTree, Category
import re

class TreeForm(forms.ModelForm):
    file = forms.FileField(label="Import", required=False)
    class Meta:
        model = ProjectTree
        fields = ['name','slug']
    def clean(self):
        cd = self.cleaned_data
        slugs = ProjectTree.objects.filter(slug=cd['slug'])
        if len(slugs) > 0:
            raise forms.ValidationError("That slug is already taken.") 
        if self.cleaned_data.get('file'):
           f = self.cleaned_data['file']
           if f.name.split('.')[-1] != 'mm' and f.name.split('.')[-1] != 'csv':
               raise forms.ValidationError("Must be either MindMap (mm) or CSV file")

class TreeEditForm(forms.ModelForm):
    class Meta:
        model = ProjectTree
        fields = ['name','slug']

    def clean(self):
        cd = self.cleaned_data
        slugs = ProjectTree.objects.filter(slug=cd['slug'])
        if len(slugs) > 0:
            raise forms.ValidationError("That slug is already taken.")

class ImportForm(forms.Form):
    file = forms.FileField(label="File", required=False)
    
    def clean(self):
       if self.cleaned_data.get('file'):
           f = self.cleaned_data['file']
           if f.name.split('.')[-1] != 'mm' and f.name.split('.')[-1] != 'csv':
               raise forms.ValidationError("Must be either MindMap (mm) or CSV file") 

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'regex']
        labels = { 'regex': "Regex (optional)" }
 
    def clean(self):
        cleaned_data = super(CategoryForm, self).clean()
        if cleaned_data['regex']:
            try:
                re.compile(cleaned_data['regex'])
            except re.error:
                raise forms.ValidationError("Invalid Regex: %s" % re.error)
        else:
            cleaned_data['regex'] = None
