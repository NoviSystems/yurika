from django.test import TestCase

from mortar import models
from mortar.api import serializers


class QueryPartSerializerTests(TestCase):
    # Indirectly tests the polymorphic serializer class.

    @classmethod
    def setUpTestData(cls):
        occurance = models.PartOfSpeechPart.OCCURANCE
        parts = models.PartOfSpeechPart.PARTS_OF_SPEECH

        cls.q = models.Query.objects.create()

        cls.dicionary_part = models.DictionaryPart.objects.create(
            query=cls.q,
            occurance=occurance.should,
            dictionary=models.Dictionary.objects.create(
                name='',
                words='abcd\nefgh\nijkl\n',
            ),
        )
        cls.pos_part = models.PartOfSpeechPart.objects.create(
            query=cls.q,
            occurance=occurance.must_not,
            part_of_speech=parts.CC,
        )

    def test_representation(self):
        # dictionary output
        serializer = serializers.QueryPartSerializer(self.dicionary_part)
        self.assertEqual(serializer.data, {
            'type': 'dictionary part',
            'occurance': 'should',
            'dictionary': 1,
        })

        # part of speech output
        serializer = serializers.QueryPartSerializer(self.pos_part)
        self.assertEqual(serializer.data, {
            'type': 'part of speech part',
            'occurance': 'must_not',
            'part_of_speech': 'CC',
        })

    def test_validation(self):
        # validate dictionary input
        serializer = serializers.QueryPartSerializer(data={
            'type': 'dictionary part',
            'occurance': 'should',
            'dictionary': 1,
        })

        serializer.is_valid(raise_exception=True)
        self.assertDictEqual(serializer.validated_data, {
            'occurance': 'should',
            'dictionary': self.dicionary_part.dictionary,
        })

        # validate part of speech input
        serializer = serializers.QueryPartSerializer(data={
            'type': 'part of speech part',
            'occurance': 'must_not',
            'part_of_speech': 'CC',
        })

        serializer.is_valid(raise_exception=True)
        self.assertEqual(serializer.validated_data, {
            'occurance': 'must_not',
            'part_of_speech': 'CC',
        })

    def test_invalid_type(self):
        # query part is not a valid type, even though it's the base class
        serializer = serializers.QueryPartSerializer(data={
            'type': 'query part',
            'occurance': 'should',
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {
            'type': [
                "Invalid type. Expected one of ['dictionary part', 'node "
                "part', 'part of speech part'], but got 'query part'."
            ],
        })

    def test_invalid_data(self):
        # test concrete type is used to validate
        serializer = serializers.QueryPartSerializer(data={
            'type': 'dictionary part',
            'occurance': 'must_not',
            'dictionary': 4
        })

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {
            'dictionary': ['Invalid pk "4" - object does not exist.'],
        })

    def test_create(self):
        # sanity check against existing data
        self.assertEqual(models.QueryPart.objects.count(), 2)

        serializer = serializers.QueryPartSerializer(data={
            'type': 'part of speech part',
            'occurance': 'must_not',
            'part_of_speech': 'FW',
        })

        # update part of speech query part
        serializer.is_valid(raise_exception=True)
        part = serializer.save(query=self.q)

        # check that part of speech query part was updated
        self.assertNotEqual(self.pos_part.pk, part.pk)
        self.assertEqual(part.pk, 3)
        self.assertEqual(part.part_of_speech, 'FW')

        # One new query parts should exist
        self.assertEqual(models.QueryPart.objects.count(), 3)

    def test_update(self):
        # sanity check against existing data
        self.assertEqual(models.QueryPart.objects.count(), 2)

        serializer = serializers.QueryPartSerializer(
            instance=self.pos_part,
            data={
                'type': 'part of speech part',
                'occurance': 'must_not',
                'part_of_speech': 'FW',
            }
        )

        # update part of speech query part
        serializer.is_valid(raise_exception=True)
        part = serializer.save()

        # check that part of speech query part was updated
        self.assertEqual(self.pos_part.pk, part.pk)
        self.assertEqual(self.pos_part.part_of_speech, 'FW')

        # No new query parts should exist
        self.assertEqual(models.QueryPart.objects.count(), 2)


class QueryPartListSerializerTests(TestCase):
    # Indirectly tests the polymorphic list serializer class.

    @classmethod
    def setUpTestData(cls):
        occurance = models.PartOfSpeechPart.OCCURANCE
        parts = models.PartOfSpeechPart.PARTS_OF_SPEECH

        cls.q = models.Query.objects.create()

        cls.dicionary_part = models.DictionaryPart.objects.create(
            query=cls.q,
            occurance=occurance.should,
            dictionary=models.Dictionary.objects.create(
                name='',
                words='abcd\nefgh\nijkl\n',
            ),
        )
        cls.pos_part = models.PartOfSpeechPart.objects.create(
            query=cls.q,
            occurance=occurance.must_not,
            part_of_speech=parts.CC,
        )

    def test_representation(self):
        # test list output - this should call `.select_subclasses()
        serializer = serializers.QueryPartSerializer(self.q.parts, many=True)
        self.assertEqual(serializer.data, [
            {
                'type': 'dictionary part',
                'occurance': 'should',
                'dictionary': 1,
            }, {
                'type': 'part of speech part',
                'occurance': 'must_not',
                'part_of_speech': 'CC',
            },
        ])

    def test_validation(self):
        # validate list of different parts
        serializer = serializers.QueryPartSerializer(data=[
            {
                'type': 'dictionary part',
                'occurance': 'should',
                'dictionary': 1,
            }, {
                'type': 'part of speech part',
                'occurance': 'must_not',
                'part_of_speech': 'CC',
            }
        ], many=True)

        serializer.is_valid(raise_exception=True)
        self.assertEqual(serializer.validated_data, [
            {
                'occurance': 'should',
                'dictionary': self.dicionary_part.dictionary,
            }, {
                'occurance': 'must_not',
                'part_of_speech': 'CC',
            }
        ])

    def test_create(self):
        # sanity check against existing data
        self.assertEqual(models.QueryPart.objects.count(), 2)

        serializer = serializers.QueryPartSerializer(data=[
            {
                'type': 'part of speech part',
                'occurance': 'must',
                'part_of_speech': 'FW',
            }, {
                'type': 'part of speech part',
                'occurance': 'must_not',
                'part_of_speech': 'JJ',
            }
        ], many=True)

        # update part of speech query part
        serializer.is_valid(raise_exception=True)
        parts = serializer.save(query=self.q)

        self.assertEqual(len(parts), 2)

        self.assertEqual(parts[0].pk, 3)
        self.assertEqual(parts[0].occurance, 'must')
        self.assertEqual(parts[0].part_of_speech, 'FW')

        self.assertEqual(parts[1].pk, 4)
        self.assertEqual(parts[1].occurance, 'must_not')
        self.assertEqual(parts[1].part_of_speech, 'JJ')

        # Two new query parts should exist
        self.assertEqual(models.QueryPart.objects.count(), 4)


class QuerySerializerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        category = models.Query.CATEGORY
        occurance = models.PartOfSpeechPart.OCCURANCE
        parts = models.PartOfSpeechPart.PARTS_OF_SPEECH

        cls.q = models.Query.objects.create(category=category.sentence)

        cls.dicionary_part = models.DictionaryPart.objects.create(
            query=cls.q,
            occurance=occurance.should,
            dictionary=models.Dictionary.objects.create(
                name='',
                words='abcd\nefgh\nijkl\n',
            ),
        )
        cls.pos_part = models.PartOfSpeechPart.objects.create(
            query=cls.q,
            occurance=occurance.must_not,
            part_of_speech=parts.CC,
        )

    def test_representation(self):
        serializer = serializers.QuerySerializer(self.q)
        self.assertEqual(serializer.data, {
            'id': 1,
            'category': 0,
            'parts': [
                {
                    'type': 'dictionary part',
                    'occurance': 'should',
                    'dictionary': 1,
                }, {
                    'type': 'part of speech part',
                    'occurance': 'must_not',
                    'part_of_speech': 'CC',
                },
            ],
        })

    def test_validated_data(self):
        # validate list of different parts
        serializer = serializers.QuerySerializer(data={
            'category': 0,
            'parts': [
                {
                    'type': 'dictionary part',
                    'occurance': 'should',
                    'dictionary': 1,
                }, {
                    'type': 'part of speech part',
                    'occurance': 'must_not',
                    'part_of_speech': 'CC',
                }
            ],
        })

        serializer.is_valid(raise_exception=True)
        self.assertEqual(serializer.validated_data, {
            'category': 0,
            'parts': [
                {
                    'occurance': 'should',
                    'dictionary': self.dicionary_part.dictionary,
                }, {
                    'occurance': 'must_not',
                    'part_of_speech': 'CC',
                }
            ],
        })

    def test_create(self):
        # sanity check against existing data
        self.assertEqual(models.Query.objects.count(), 1)
        self.assertEqual(models.QueryPart.objects.count(), 2)
        self.assertEqual(models.Query.objects.first().parts.count(), 2)

        serializer = serializers.QuerySerializer(data={
            'category': 0,
            'parts': [
                {
                    'type': 'dictionary part',
                    'occurance': 'should',
                    'dictionary': 1,
                }, {
                    'type': 'part of speech part',
                    'occurance': 'must_not',
                    'part_of_speech': 'CC',
                }
            ],
        })
        serializer.is_valid(raise_exception=True)
        query = serializer.save()

        self.assertEqual(models.Query.objects.count(), 2)
        self.assertEqual(models.QueryPart.objects.count(), 4)
        self.assertEqual(models.Query.objects.first().parts.count(), 2)
        self.assertEqual(query.parts.count(), 2)

    def test_update(self):
        # sanity check against existing data
        self.assertEqual(models.Query.objects.count(), 1)
        self.assertEqual(models.QueryPart.objects.count(), 2)
        self.assertEqual(models.Query.objects.first().parts.count(), 2)

        serializer = serializers.QuerySerializer(self.q, data={
            'category': 0,
            'parts': [
                {
                    'type': 'part of speech part',
                    'occurance': 'must',
                    'part_of_speech': 'FW',
                }, {
                    'type': 'part of speech part',
                    'occurance': 'must_not',
                    'part_of_speech': 'JJ',
                }
            ],
        })
        serializer.is_valid(raise_exception=True)
        query = serializer.save()
        parts = query.parts.select_subclasses()

        # check updated query parts
        self.assertEqual(len(parts), 2)

        self.assertEqual(parts[0].pk, 3)
        self.assertEqual(parts[0].occurance, 'must')
        self.assertEqual(parts[0].part_of_speech, 'FW')

        self.assertEqual(parts[1].pk, 4)
        self.assertEqual(parts[1].occurance, 'must_not')
        self.assertEqual(parts[1].part_of_speech, 'JJ')

        # No new parts should exist
        self.assertEqual(models.Query.objects.count(), 1)
        self.assertEqual(models.QueryPart.objects.count(), 2)
        self.assertEqual(models.Query.objects.first().parts.count(), 2)
        self.assertEqual(query.parts.count(), 2)
