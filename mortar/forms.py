from django import forms
from django.conf import settings
from django.db.models import Q
from django.utils.text import slugify
import mortar.models as models
import re

class ConfigureForm(forms.Form):
    seed_list = forms.CharField(widget=forms.Textarea, required=False)
    file = forms.FileField(label="Import MindMap", required=False)
    part_type = forms.ChoiceField(choices=((0, 'Regular Expression'), (1, 'Dictionary'), (2, 'Part of Speech')))
    regex = forms.ModelChoiceField(queryset=models.Node.objects.filter(tree_link__slug='default').distinct(), required=False)
    part_of_speech = forms.ChoiceField(choices=settings.PARTS_OF_SPEECH)
    dictionary = forms.ModelChoiceField(queryset=models.Dictionary.objects.all(), required=False)
    op = forms.ChoiceField(choices=((0, 'OR'), (1, 'AND')), label="Operation")

    category = forms.ChoiceField(choices=(('S', 'Sentence'), ('P', 'Paragraph'), ('D', 'Document')), label='Type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

class BSModelForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class QueryForm(forms.Form):
    category = forms.ChoiceField(choices=(('S', 'Sentence'), ('P', 'Paragraph'), ('D', 'Document')), label='Type')
    
class CrawlerForm(BSModelForm):
    index = forms.ModelChoiceField(queryset=models.ElasticIndex.objects.filter(crawlers__isnull=False).distinct(), required=False, label="Document Index")
    new_index = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class':'form-control', 'autocomplete': 'off', 'pattern': '[0-9a-zA-Z]+', 'title': 'Alphanumeric characters only'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        self.fields['index'].empty_label = 'New Index'

    def clean(self):
        data = super(CrawlerForm, self).clean()
        if not data['index'] and not data['new_index']:
            raise forms.ValidationError('Must choose Index or create new one')
        elif not data['index'] and data['new_index']:
            new_ei, created = models.ElasticIndex.objects.get_or_create(name=data['new_index'])
            if not created:
                raise forms.ValidationError('Index name already exists. Please choose another')
            data['index'] = new_ei
        return data

    class Meta:
        model = models.Crawler
        fields = ['name', 'category', 'index']
        labels = {'name': 'Name','category': 'Crawler Type','index': 'Elastic Index'}


class TreeForm(BSModelForm):
    file = forms.FileField(label='Import', required=False)
    doc_source = forms.ModelChoiceField(queryset=models.ElasticIndex.objects.all(), required=False, label='Source Index')
    doc_dest = forms.ModelChoiceField(queryset=models.ElasticIndex.objects.filter(Q(doc_sources__isnull=False) | Q(doc_dests__isnull=False)).distinct(), required=False, label='Destination Index')
    new_source_index = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class':'form-control', 'autocomplete': 'off', 'pattern': '[0-9a-zA-Z]+', 'title': 'Alphanumeric characters only'}))
    new_dest_index = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class':'form-control', 'autocomplete': 'off', 'pattern': '[0-9a-zA-Z]+', 'title': 'Alphanumeric characters only'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        self.fields['doc_source'].empty_label = 'New Index'
        self.fields['doc_dest'].empty_label = 'New Index'

    def clean(self):
        data = super(TreeForm, self).clean()
        if not data['new_source_index'] and not data['doc_source'] or not data['new_dest_index'] and not data['doc_dest']:
            raise forms.ValidationError('Must choose index or create new one')
        else:
            if not data['doc_source'] and data['new_source_index']:
                new_ei, created = models.ElasticIndex.objects.get_or_create(name=data['new_source_index'])
                data['doc_source'] = new_ei
            if not data['doc_dest'] and data['new_dest_index']:
                new_ei, created = models.ElasticIndex.objects.get_or_create(name=data['new_dest_index'])
                data['doc_dest'] = new_ei
        return data

    class Meta:
        model = models.Tree
        fields = ['name']

class DictionaryForm(BSModelForm):
    words = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = models.Dictionary
        fields = ['name']

class WordForm(BSModelForm):
    class Meta:
        model = models.Word
        fields = ['name']

class TreeEditForm(BSModelForm):
    doc_source_index = forms.ModelChoiceField(queryset=models.ElasticIndex.objects.all(), required=False, label='Source Index')
    doc_dest_index = forms.ModelChoiceField(queryset=models.ElasticIndex.objects.filter(Q(doc_sources__isnull=False) | Q(doc_dests__isnull=False)).distinct(), required=False, label='Destination Index')
    new_source_index = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class':'form-control', 'autocomplete': 'off', 'pattern': '[0-9a-zA-Z]+', 'title': 'Alphanumeric characters only'}))
    new_dest_index = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class':'form-control', 'autocomplete': 'off', 'pattern': '[0-9a-zA-Z]+', 'title': 'Alphanumeric characters only'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        self.fields['doc_source_index'].empty_label = 'New Index'
        self.fields['doc_dest_index'].empty_label = 'New Index'

    def clean(self):
        data = super(TreeEditForm, self).clean()
        if 'slug' in self.changed_data:
            slugs = models.Tree.objects.filter(slug=data['slug'])
            if len(slugs) > 0:
                raise forms.ValidationError('That slug is already taken.')

        if not data['new_source_index'] and not data['doc_source_index'] or not data['new_dest_index'] and not data['doc_dest_index']:
            raise forms.ValidationError('Must choose index or create new one')
        else:
            if not data['doc_source_index'] and data['new_source_index']:
                new_ei, created = models.ElasticIndex.objects.get_or_create(name=data['new_source_index'])
                data['doc_source_index'] = new_ei
            if not data['doc_dest_index'] and data['new_dest_index']:
                new_ei, created = models.ElasticIndex.objects.get_or_create(name=data['new_dest_index'])
                data['doc_dest_index'] = new_ei
        print(data)
        return data
  
    class Meta:
        model = models.Tree
        fields = ['name', 'slug', 'doc_source_index', 'doc_dest_index']



class MindMapImportForm(forms.Form):
    file = forms.FileField(label='File', required=False)

    def clean(self):
        if self.cleaned_data.get('file'):
            f = self.cleaned_data['file']
            if f.name.split('.')[-1] != 'mm':
                raise forms.ValidationError('Must be MindMap (mm) file')


class NodeForm(BSModelForm):

    class Meta:
        model = models.Node
        fields = ['name', 'regex']
        labels = {'regex': 'Regex (optional)'}

    def clean(self):
        cleaned_data = super(NodeForm, self).clean()
        if cleaned_data['regex']:
            try:
                re.compile(cleaned_data['regex'])
            except re.error:
                raise forms.ValidationError('Invalid Regex: %s' % re.error)

        else:
            cleaned_data['regex'] = None


class DictionaryPartForm(BSModelForm):

    class Meta:
        model = models.DictionaryPart
        fields = ['dictionary', 'op']
        labels = {'dictionary': 'Dictionary','op': 'Operation'}


class RegexPartForm(BSModelForm):

    class Meta:
        model = models.RegexPart
        fields = ['regex', 'op']
        labels = {'regex': 'Regular Expression','op': 'Operation'}


class SubQueryPartForm(BSModelForm):

    class Meta:
        model = models.SubQueryPart
        fields = ['subquery', 'op']
        labels = {'subquery': 'Combined Query','op': 'Operation'}


class PartOfSpeechPartForm(BSModelForm):

    class Meta:
        model = models.PartOfSpeechPart
        fields = ['part_of_speech', 'op']
        labels = {'part_of_speech': 'Part of Speech','op': 'Operation'}


class QuerySelectForm(forms.Form):
    query = forms.ModelChoiceField(queryset=models.Query.objects.all(), label='Queries', required=False)
    category = forms.ChoiceField(choices=(('S', 'Sentence'), ('P', 'Paragraph'), ('D', 'Document')), label='Type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
