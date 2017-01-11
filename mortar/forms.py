from django import forms
from django.utils.text import slugify
from .models import ProjectTree, Category
import re

class TreeForm(forms.ModelForm):
    populate = forms.BooleanField(label="Populate default PESTLE?", required=False, initial=False)
    class Meta:
        model = ProjectTree
        fields = ['name',]

class ImportForm(forms.Form):
    file = forms.FileField(label="File", required=False)

class CategoryForm(forms.Form):
    name = forms.CharField(label="Name")
    is_rule = forms.BooleanField(label="Rule?", initial=False, required=False)
    regex = forms.CharField(label="Regex", required=False)
   
    def clean(self):
        cleaned_data = super(CategoryForm, self).clean()
        if cleaned_data['is_rule']:
            try:
                re.compile(cleaned_data['regex'])
            except re.error:
                raise forms.ValidationError("Invalid Regex: %s" % re.error)
        else:
            cleaned_data['regex'] = None
