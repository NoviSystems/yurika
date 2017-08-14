from django import forms
from django.utils.text import slugify
import mortar.models as models
import re

class ProjectForm(forms.ModelForm):
    class Meta:
        model = models.Project
        fields = ['name', 'slug']

class TreeForm(forms.ModelForm):
    file = forms.FileField(label="Import", required=False)
    class Meta:
        model = models.ProjectTree
        fields = ['name','slug']
    def clean(self):
        cd = self.cleaned_data
        slugs = models.ProjectTree.objects.filter(slug=cd['slug'])
        if len(slugs) > 0:
            raise forms.ValidationError("That slug is already taken.") 
        if self.cleaned_data.get('file'):
           f = self.cleaned_data['file']
           if f.name.split('.')[-1] != 'mm' and f.name.split('.')[-1] != 'csv':
               raise forms.ValidationError("Must be either MindMap (mm) or CSV file")

class TreeEditForm(forms.ModelForm):
    class Meta:
        model = models.ProjectTree
        fields = ['name','slug']

    def clean(self):
        cd = self.cleaned_data
        slugs = models.ProjectTree.objects.filter(slug=cd['slug'])
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
        model = models.Category
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

class AnnotationQueryForm(forms.Form):
    dictionaries = forms.ModelMultipleChoiceField(queryset=models.AIDictionary.objects.all(), label="Dictionaries", required=False)
    andor = forms.ChoiceField(widget=forms.RadioSelect, choices=(('and', 'AND'), ('or', 'OR')), label="And/Or", required=False)
    regexs = forms.ModelMultipleChoiceField(queryset=models.Category.objects.all(), label="Regexs", required=False)
    annotype = forms.ChoiceField(widget=forms.RadioSelect, choices=(('S', 'Sentence'), ('P', 'Paragraph')), label="Annotation Type", initial='S')

    def clean(self):
        cd = super(AnnotationQueryForm, self).clean()
        if cd['dictionaries'] and cd['regexs'] and not cd['andor']:
            raise forms.ValidationError("Must select And/Or")
        if not cd['dictionaries'] and not cd['regexs']:
            raise forms.ValidationError("Must select at least one dictionary or tree node")
        if not cd['dictionaries'] or not cd['regexs']:
            cd['andor'] = None

class BSModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = "form-control"


class DictionaryPartForm(BSModelForm):
    class Meta:
        model = models.DictionaryPart
        fields = ['dictionary', 'op']
        labels = {'dictionary': 'Dictionary', 'op': 'Operation'}

class RegexPartForm(BSModelForm):
    class Meta:
        model = models.RegexPart
        fields = ['regex', 'op']
        labels = {'regex': 'Regular Expression', 'op': 'Operation'}

class SubQueryPartForm(BSModelForm):
    class Meta:
        model = models.SubQueryPart
        fields = ['subquery', 'op']
        labels = {'subquery': 'Combined Query', 'op': 'Operation'}

class PartOfSpeechPartForm(BSModelForm):
    class Meta:
        model = models.PartOfSpeechPart
        fields = ['part_of_speech', 'op']
        labels = {'part_of_speech': 'Part of Speech', 'op': 'Operation'}

class QuerySelectForm(forms.Form):
    query = forms.ModelChoiceField(queryset=models.Query.objects.all(), label="Queries", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = "form-control"
