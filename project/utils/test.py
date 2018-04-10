import os
import sys
from atexit import register
from contextlib import contextmanager
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import TransactionTestCase, client
from django.urls import reverse
from dramatiq import Worker, get_broker
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


opts = Options()
opts.add_argument("--headless")
opts.add_argument("--window-size=1920x1080")


# Use a shared chromedriver instance given slow startup speed
driver = webdriver.Chrome(executable_path='chromedriver', chrome_options=opts)
register(driver.quit)


class SeleniumClient(client.Client):

    def add_cookie(self, name, **opts):
        value = self.cookies[name].value

        current_url = self.driver.current_url
        if not current_url.startswith(self.server_url):
            self.driver.get(self.server_url)

        self.driver.add_cookie({
            'name': name,
            'value': value,
            **opts
        })

    def login(self, **credentials):
        super().login(**credentials)
        self.add_cookie(settings.SESSION_COOKIE_NAME)

    def force_login(self, user, backend=None):
        super().force_login(user, backend)
        self.add_cookie(settings.SESSION_COOKIE_NAME)

    @contextmanager
    def logged_in(self, **credentials):
        try:
            self.login(**credentials)
            yield
        finally:
            self.logout()


class FunctionalTestCase(StaticLiveServerTestCase):
    client_class = SeleniumClient

    def _pre_setup(self):
        super()._pre_setup()
        self.driver = driver
        self.domain = urlparse(self.live_server_url).hostname

        self.client.driver = self.driver
        self.client.server_url = self.live_server_url

    def _post_teardown(self):
        if sys.exc_info()[0]:
            test_name = f'{self.__module__}.{self.__class__.__name__}.{self._testMethodName}'
            self.save_logs(f'debug/{test_name}.logs')
            self.save_page(f'debug/{test_name}.html')
            assert self.save_screenshot(f'debug/{test_name}.png'), \
                f"Failed to save screenshot for {self._testMethodName}."

        self.driver.delete_all_cookies()
        self.driver.refresh()
        super()._post_teardown()

    def ensure_pathdirs(self, path):
        path = os.path.abspath(os.path.join(settings.BASE_DIR, path))
        directory = os.path.dirname(path)

        if not os.path.exists(directory):
            os.makedirs(directory)

    def save_logs(self, path):
        self.ensure_pathdirs(path)

        with open(path, 'w') as file:
            for line in self.driver.get_log('browser'):
                file.write('%s: %s\n' % (line['level'], line['message']))

    def save_page(self, path):
        self.ensure_pathdirs(path)

        with open(path, 'wb') as file:
            file.write(self.driver.page_source.encode('utf-8'))

    def save_screenshot(self, path):
        self.ensure_pathdirs(path)

        self.driver.set_window_size(1920, 1080)
        return self.driver.save_screenshot(path)

    def url(self, name):
        """
        Shortcut for generating the absolute url of the given url name.
        """
        path = reverse(name)
        return urljoin(self.live_server_url, path)

    def select(self, selector):
        return self.driver.find_element_by_css_selector(selector)

    def exists(self, selector):
        try:
            self.select(selector)
        except NoSuchElementException:
            return False
        return True

    def wait_until(self, selector, timeout=3):
        """
        Waits until ``selector`` is found in the driver, or until ``timeout``
        is hit, whichever happens first.
        """
        WebDriverWait(self.driver, timeout).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, selector)
            )
        )

        return self

    def wait_until_not(self, selector, timeout=3):
        """
        Waits until ``selector`` is NOT found in the driver, or until
        ``timeout`` is hit, whichever happens first.
        """
        WebDriverWait(self.driver, timeout).until_not(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, selector)
            )
        )

        return self


# Note: can be deleted once merged into django_dramatiq
class DramatiqTestCase(TransactionTestCase):

    def _pre_setup(self):
        super()._pre_setup()

        self.broker = get_broker()
        self.broker.flush_all()

        self.worker = Worker(self.broker, worker_timeout=100)
        self.worker.start()

    def _post_teardown(self):
        self.worker.stop()

        super()._post_teardown()
