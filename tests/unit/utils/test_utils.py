from datetime import timedelta

from django.test import TestCase

from yurika import utils


class HumanizeTimedeltaTests(TestCase):
    def test_output(self):
        testcases = [
            (timedelta(seconds=60), "1 minutes"),
            (timedelta(minutes=1), "1 minutes"),
            (timedelta(seconds=119), "1 minutes, 59 seconds"),
            (timedelta(minutes=1, seconds=59), "1 minutes, 59 seconds"),
            (timedelta(hours=240), "10 days"),
            (timedelta(days=10), "10 days"),
            (timedelta(seconds=1234), "20 minutes, 34 seconds"),
            (timedelta(days=2, seconds=14), "2 days, 14 seconds")
        ]

        for td, expected in testcases:
            with self.subTest(timedelta=td, expected_output=expected):
                self.assertEqual(utils.humanize_timedelta(td), expected)
