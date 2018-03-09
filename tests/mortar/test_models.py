from django.test import TestCase

from mortar import models


class QueryTests(TestCase):
    def test_json_occurance_grouping(self):
        occurance = models.PartOfSpeechPart.OCCURANCE
        parts = models.PartOfSpeechPart.PARTS_OF_SPEECH

        q = models.Query.objects.create(
            category=models.Query.CATEGORY.sentence,
        )

        models.PartOfSpeechPart.objects.create(
            query=q,
            occurance=occurance.must,
            part_of_speech=parts.CC,
        )
        models.PartOfSpeechPart.objects.create(
            query=q,
            occurance=occurance.must,
            part_of_speech=parts.CD,
        )
        models.PartOfSpeechPart.objects.create(
            query=q,
            occurance=occurance.should,
            part_of_speech=parts.EX,
        )
        models.PartOfSpeechPart.objects.create(
            query=q,
            occurance=occurance.must_not,
            part_of_speech=parts.FW,
        )
        models.PartOfSpeechPart.objects.create(
            query=q,
            occurance=occurance.must_not,
            part_of_speech=parts.RB,
        )

        self.assertEqual(q.json(), {
            'bool': {
                'must': [
                    {'match': {'tokens': '|CC'}},
                    {'match': {'tokens': '|CD'}},
                ],
                'should': [
                    {'match': {'tokens': '|EX'}},
                ],
                'must_not': [
                    {'match': {'tokens': '|FW'}},
                    {'match': {'tokens': '|RB'}},
                ],
            },
        })
