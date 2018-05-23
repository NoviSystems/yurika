from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from project.utils import validators


class DomainField(serializers.CharField):
    """
    A `RegexField` that validates the input against a domain-matching pattern.
    Domains may be prefixed with a leading "." to indicate all sub-domains.
    """
    default_error_messages = {
        'invalid': _('Enter a valid domain.')
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validators.append(
            validators.DomainValidator(message=self.error_messages['invalid'])
        )


class TextListField(serializers.ListField):
    """
    Text-based `ListField` where values are separated by new lines.
    """

    def to_internal_value(self, data):
        return '\n'.join(str(value) for value in super().to_internal_value(data))

    def to_representation(self, data):
        return super().to_representation(data.splitlines())
