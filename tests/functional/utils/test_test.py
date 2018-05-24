from django.contrib.auth import get_user_model

from project.utils.test import FunctionalTestCase


User = get_user_model()


class FunctionalTestCaseTests(FunctionalTestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='username', password='password')

    def test_login(self):
        self.assertNotIn('username', self.driver.page_source)

        self.client.login(username='username', password='password')

        self.driver.get(self.url('home'))
        self.assertIn('username', self.driver.page_source)

    def test_force_login(self):
        self.assertNotIn('username', self.driver.page_source)

        self.client.force_login(self.user)

        self.driver.get(self.url('home'))
        self.assertIn('username', self.driver.page_source)

    def test_url(self):
        self.assertEqual(self.url('login'), '%s/login/' % self.live_server_url)
