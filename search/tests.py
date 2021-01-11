from django.test import TestCase
from .query import calc_starting_row


class UtilTestCase(TestCase):
    # Pagination test

    def test_calc_starting_row(self):
        start_page = calc_starting_row(34, 10)
        self.assertEqual(start_page[0], 330)
