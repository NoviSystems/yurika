from django.test import TestCase
from rest_framework import serializers

from yurika.api import fields


def get_items(value):
    if isinstance(value, dict):
        return value.items()
    elif isinstance(value, (tuple, list)):
        return [i for i in value]


class FieldValues:
    """
    Base class for testing valid and invalid input values. Based on:
    https://github.com/encode/django-rest-framework/blob/3.8.2/tests/test_fields.py#L538-L563
    """

    def test_valid_inputs(self):
        """
        Ensure that valid values return the expected validated data.
        """
        for input_value, expected_output in get_items(self.valid_inputs):
            with self.subTest(input_value=input_value, expected_output=expected_output):
                result = self.field.run_validation(input_value)
                self.assertEqual(result, expected_output)

    def test_invalid_inputs(self):
        """
        Ensure that invalid values raise the expected validation error.
        """
        for input_value, expected_failure in get_items(self.invalid_inputs):
            with self.subTest(input_value=input_value, expected_failure=expected_failure):
                with self.assertRaises(serializers.ValidationError) as exc_info:
                    self.field.run_validation(input_value)
                self.assertEqual(exc_info.exception.detail, expected_failure)

    def test_outputs(self):
        for output_value, expected_output in get_items(self.outputs):
            with self.subTest(output_value=output_value, expected_output=expected_output):
                result = self.field.to_representation(output_value)
                self.assertEqual(result, expected_output)


class DomainFieldTests(FieldValues, TestCase):
    field = fields.DomainField()
    valid_inputs = {
        'example.com': 'example.com',
        'مثال.إختبار': 'مثال.إختبار',
    }
    invalid_inputs = {
        'http://example.com': ['Enter a valid domain.']
    }
    outputs = {}


class TestListFieldTests(FieldValues, TestCase):
    field = fields.TextListField(child=serializers.IntegerField())
    valid_inputs = [
        ([1, 2, 3], '1\n2\n3'),
        (['1', '2', '3'], '1\n2\n3'),
        (['1    ', '2', '3'], '1\n2\n3'),
        ([], '')
    ]
    invalid_inputs = [
        ([1, 2, 'error', 'error'], {2: ['A valid integer is required.'], 3: ['A valid integer is required.']}),
    ]
    outputs = [
        ('1\n2\n3', [1, 2, 3]),
        ('1  \n  2\n3', [1, 2, 3]),
    ]
