from django.test import TestCase

from mortar.dictionary_utils import token_chains


class TokenTermTests(TestCase):

    def test_simple(self):
        term_tokens = {
            'a': {'tokens': [{'position': 1}]},
            'b': {'tokens': [{'position': 2}]},
            'c': {'tokens': [{'position': 3}]},
        }

        result = token_chains(['a', 'b', 'c'], term_tokens)
        self.assertListEqual(result, [
            [{'position': 1}, {'position': 2}, {'position': 3}],
        ])

    def test_multiple(self):
        term_tokens = {
            'a': {'tokens': [{'position': 1}, {'position': 7}]},
            'b': {'tokens': [{'position': 2}, {'position': 8}]},
            'c': {'tokens': [{'position': 3}, {'position': 9}]},
        }

        result = token_chains(['a', 'b', 'c'], term_tokens)
        self.assertListEqual(result, [
            [{'position': 1}, {'position': 2}, {'position': 3}],
            [{'position': 7}, {'position': 8}, {'position': 9}],
        ])

    def test_non_sequential(self):
        term_tokens = {
            'a': {'tokens': [{'position': 1}]},
            'b': {'tokens': [{'position': 3}]},
            'c': {'tokens': [{'position': 5}]},
        }

        result = token_chains(['a', 'b', 'c'], term_tokens)
        self.assertListEqual(result, [])

    def test_missing(self):
        term_tokens = {
            'a': {'tokens': [{'position': 1}]},
            'c': {'tokens': [{'position': 3}]},
        }

        result = token_chains(['a', 'b', 'c'], term_tokens)
        self.assertListEqual(result, [])
