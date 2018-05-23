from django.forms.fields import FileField
from django.forms.forms import BaseForm
from django.utils.safestring import mark_safe


class TemplateForm(BaseForm):
    """
    This mixin should precede `forms.Form` or `forms.ModelForm` to ensure that
    the correct rendering method is called.
    """
    template_name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, FileField):
                continue
            field.widget.attrs['class'] = 'form-control'

    def get_template(self, field):
        raise NotImplementedError

    def get_form_context(self):
        return {
            'form': self,
        }

    def render(self):
        context = self.get_form_context()

        return mark_safe(self.renderer.render(self.template_name, context))

    def __str__(self):
        return self.render()


class BlockForm(TemplateForm):
    template_name = 'utils/forms/block.html'

    def get_template(self, field):
        return 'utils/forms/fields/block.html'


class HorizontalForm(TemplateForm):
    template_name = 'utils/forms/horizontal.html'

    def get_template(self, field):
        return 'utils/forms/fields/horizontal.html'
