from django.contrib.auth import get_user_model

from yurika.utils.test import FunctionalTestCase


User = get_user_model()


class LoginTests(FunctionalTestCase):

    def setUp(self):
        User.objects.create_user(username='user', password='password')

    def test_login(self):
        self.driver.get(self.url('login'))

        self.assertIn('Please login', self.driver.page_source)

        self.driver \
            .find_element_by_name('username') \
            .send_keys('user')
        self.driver \
            .find_element_by_name('password') \
            .send_keys('password')
        self.select('form').submit()

        self.assertEqual(self.url('home'), self.driver.current_url)
        self.assertInHTML('Home page', self.driver.page_source)
        self.assertInHTML('Logged in as user', self.driver.page_source)

        logout = self.select('.navbar .navbar-nav:last-child') \
                     .find_element_by_css_selector('a:last-child')
        self.assertEqual(logout.text, 'Log out')


class HomePageTests(FunctionalTestCase):

    def setUp(self):
        User.objects.create_user(username='user', password='password')

    def test_unauthenticated(self):
        self.driver.get(self.url('home'))
        self.assertInHTML('Home page', self.driver.page_source)
        self.assertNotIn('Logged in as user', self.driver.page_source)

    def test_authenticated(self):
        self.client.login(username='user', password='password')

        self.driver.get(self.url('home'))
        self.assertInHTML('Home page', self.driver.page_source)
        self.assertInHTML('Logged in as user', self.driver.page_source)

        logout = self.select('.navbar .navbar-nav:last-child') \
                     .find_element_by_css_selector('a:last-child')
        self.assertEqual(logout.text, 'Log out')
