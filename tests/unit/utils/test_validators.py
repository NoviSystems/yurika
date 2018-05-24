from django.core.exceptions import ValidationError
from django.test import TestCase

from project.utils import validators


class DomainValidatorTests(TestCase):
    valid_domains = [
        'localhost',
        'example.com',
        'example.com.',
        '.example.com',
        'sub.domain.com',
        '.sub.domain.com',
        'nested.sub.domain.com',
        '.nested.sub.domain.com',
        'مثال.إختبار',
        '.مثال.إختبار',
    ]

    invalid_domains = [
        'com',
        'com.',
        '//example.com',
        '://example.com',
        'https://example.com',

        'example.com/',
        'example.com/path',
        'example.com:80',
        'example.com:80/path',

        'example.com?query',
        'example.com/path?query',
        'example.com:80?query',
        'example.com:80/path?query',

        'example.com#fragment',
        'example.com/path#fragment',
        'example.com:80#fragment',
        'example.com:80/path#fragment',

        '0.0.0.0',
        '255.255.255.255',
        '[::1]',
    ]

    def test_valid(self):
        validator = validators.DomainValidator()

        for domain in self.valid_domains:
            with self.subTest(domain=domain):
                validator(domain)

    def test_invalid(self):
        validator = validators.DomainValidator()
        msg = "Enter a valid domain."

        for domain in self.invalid_domains:
            with self.subTest(domain=domain):
                with self.assertRaisesMessage(ValidationError, msg):
                    validator(domain)
