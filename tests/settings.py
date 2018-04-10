from project.common_settings import *  # flake8: noqa


INSTALLED_APPS += [
    'tests.integration.mortar.testapp',
]


# Store outgoing test emails in django.core.mail.outbox`.
# https://docs.djangoproject.com/en/2.0/topics/testing/tools/#email-services
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Use stub broker in testing
DRAMATIQ_BROKER['BROKER'] = 'dramatiq.brokers.stub.StubBroker'
DRAMATIQ_BROKER['OPTIONS'] = {}


# Disable most logging
LOGGING['root']['level'] = 'WARNING'
