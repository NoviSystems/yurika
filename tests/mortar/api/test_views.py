from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from mortar import models

User = get_user_model()


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
        occurance = models.PartOfSpeechPart.OCCURANCE
        parts = models.PartOfSpeechPart.PARTS_OF_SPEECH

        # setup existing query
        query = models.Query.objects.create()

        models.DictionaryPart.objects.create(
            query=query,
            occurance=occurance.should,
            dictionary_id=1,
        )
        models.PartOfSpeechPart.objects.create(
            query=query,
            occurance=occurance.must_not,
            part_of_speech=parts.CC,
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
