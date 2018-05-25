import os.path
import tempfile

from django.test import TestCase

from yurika import __main__ as main
from yurika.utils import capture_output


SETUP_STDOUT = """\
Yurika settings created...
Yurika environment file created...

Done!
"""


class YurikaSetupTests(TestCase):

    def test_dev_output(self):
        with tempfile.TemporaryDirectory() as dirname, \
                capture_output() as out:
            settings_path = os.path.join(dirname, 'settings.py')
            env_path = os.path.join(dirname, 'yurika.env')

            # Initialize Yurika
            main.init([dirname, '--dev'])

            # Check file contents
            with open(settings_path) as file:
                self.assertEqual(file.read(), main.DEV_SETTINGS)

            with open(env_path) as file:
                self.assertEqual(file.read(), main.DEV_ENVFILE)

            # Check stdout/stderr
            stdout, stderr = out
            stdout.seek(0), stderr.seek(0)
            self.assertEqual(stdout.read(), SETUP_STDOUT)
            self.assertEqual(stderr.read(), '')

    def test_prod_output(self):
        with tempfile.TemporaryDirectory() as dirname, \
                capture_output() as out:
            settings_path = os.path.join(dirname, 'settings.py')
            env_path = os.path.join(dirname, 'yurika.env')

            # Initialize Yurika
            main.init([dirname])

            # Check file contents
            with open(settings_path) as file:
                self.assertEqual(file.read(), main.PROD_SETTINGS)

            with open(env_path) as file:
                self.assertEqual(file.read(), main.PROD_ENVFILE)

            # Check stdout/stderr
            stdout, stderr = out
            stdout.seek(0), stderr.seek(0)
            self.assertEqual(stdout.read(), SETUP_STDOUT)
            self.assertEqual(stderr.read(), '')

    def test_directory_nonexistent(self):
        dirname = os.path.abspath('/does/not/exist')
        message = f"Directory '{dirname}' does not exist."

        # Attempt to initialize Yurika
        with self.assertRaises(SystemExit), \
                capture_output() as out:
            main.init([dirname])

        # Check stdout/stderr
        stdout, stderr = out
        stdout.seek(0), stderr.seek(0)
        self.assertEqual(stdout.read(), '')
        self.assertIn(message, stderr.read())

    def test_settings_exists(self):
        with tempfile.TemporaryDirectory() as dirname:
            settings_path = os.path.join(dirname, 'settings.py')
            message = f"A file already exists at '{settings_path}'."

            # Create pre-existing file
            with open(settings_path, 'w') as file:
                file.write('')

            # Attempt to initialize Yurika
            with self.assertRaises(SystemExit), \
                    capture_output() as out:
                main.init([dirname])

            # Check stdout/stderr
            stdout, stderr = out
            stdout.seek(0), stderr.seek(0)
            self.assertEqual(stdout.read(), '')
            self.assertIn(message, stderr.read())

    def test_envfile_exists(self):
        with tempfile.TemporaryDirectory() as dirname:
            envfile_path = os.path.join(dirname, 'yurika.env')
            message = f"A file already exists at '{envfile_path}'."

            # Create pre-existing file
            with open(envfile_path, 'w') as file:
                file.write('')

            # Attempt to initialize Yurika
            with self.assertRaises(SystemExit), \
                    capture_output() as out:
                main.init([dirname])

            # Check stdout/stderr
            stdout, stderr = out
            stdout.seek(0), stderr.seek(0)
            self.assertEqual(stdout.read(), '')
            self.assertIn(message, stderr.read())
