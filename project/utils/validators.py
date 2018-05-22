from django.core.validators import RegexValidator
from django.core.validators import URLValidator as U
from django.utils.translation import gettext_lazy as _


class DomainValidator(RegexValidator):
    """Validate domain names such as 'example.com'."""
    regex = f'^(\\.?{U.hostname_re}{U.domain_re}{U.tld_re}|localhost)$'
    message = _('Enter a valid domain.')
