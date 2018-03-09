from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from mortar import models


User = get_user_model()


CATEGORY = models.Query.CATEGORY
OCCURANCE = models.QueryPart.OCCURANCE
PARTS_OF_SPEECH = models.PartOfSpeechPart.PARTS_OF_SPEECH


class QueryViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(
            username='johnyboy',
            password='password',
        )

        models.Dictionary.objects.create(
            name='dictionary',
            words='abcd\nefgh\nijkl\n',
        )

    def test_create(self):
        # sanity check against existing data
        self.assertEqual(models.Query.objects.count(), 0)
        self.assertEqual(models.QueryPart.objects.count(), 0)

        data = {
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
        }

        self.client.login(username='johnyboy', password='password')
        response = self.client.post(reverse('query-list'), data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(models.Query.objects.count(), 1)
        self.assertEqual(models.QueryPart.objects.count(), 2)

    def test_update(self):
        # setup existing query
        query = models.Query.objects.create(category=CATEGORY.sentence)

        models.DictionaryPart.objects.create(
            query=query,
            occurance=OCCURANCE.should,
            dictionary_id=1,
        )
        models.PartOfSpeechPart.objects.create(
            query=query,
            occurance=OCCURANCE.must_not,
            part_of_speech=PARTS_OF_SPEECH.CC,
        )

        # sanity check against existing data
        self.assertEqual(models.Query.objects.count(), 1)
        self.assertEqual(models.QueryPart.objects.count(), 2)
        self.assertEqual(models.Query.objects.first().parts.count(), 2)

        data = {
            'category': 0,
            'parts': [{
                'type': 'part of speech part',
                'occurance': 'must',
                'part_of_speech': 'FW',
            }],
        }

        self.client.login(username='johnyboy', password='password')
        response = self.client.put(reverse('query-detail', args=[1]), data, format='json')

        # Only one part should exist for the query now
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(models.Query.objects.count(), 1)
        self.assertEqual(models.QueryPart.objects.count(), 1)
