from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts import models as accounts


class CrawlerViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = accounts.User.objects.create_user(
            username='test',
            password='test',
        )

    def test_create(self):
        url = reverse('crawler-list')
        data = {'start_urls': ['http://localhost']}

        self.client.login(username='test', password='test')

        # There should be no crawlers
        response = self.client.get(url)
        self.assertEqual(response.data['count'], 0)

        # Create a crawler
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # There should be a single crawler visible to the user
        response = self.client.get(url)
        self.assertEqual(response.data['count'], 1)
