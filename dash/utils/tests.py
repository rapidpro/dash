from __future__ import unicode_literals

import json
import pytz

from datetime import datetime
from django.core.cache import cache
from . import intersection, union, random_string, filter_dict, get_cacheable, get_obj_cacheable, get_month_range, chunks
from ..test import DashTest


class InitTest(DashTest):
    def test_intersection(self):
        self.assertEqual(intersection(), [])
        self.assertEqual(intersection([1]), [1])
        self.assertEqual(intersection([2, 1, 1]), [2, 1])
        self.assertEqual(intersection([3, 2, 1], [2, 3, 4]), [3, 2])  # order from first list
        self.assertEqual(intersection([4, 3, 2, 1], [3, 2, 4], [1, 2, 3]), [3, 2])

    def test_union(self):
        self.assertEqual(union(), [])
        self.assertEqual(union([1]), [1])
        self.assertEqual(union([2, 1, 1], [1, 2, 3]), [2, 1, 3])  # order is first seen
        self.assertEqual(union([2, 1], [2, 3, 3], [4, 5]), [2, 1, 3, 4, 5])

    def test_random_string(self):
        rs = random_string(1000)
        self.assertEqual(1000, len(rs))
        self.assertFalse('1' in rs or 'I' in rs or '0' in rs or 'O' in rs)

    def test_filter_dict(self):
        d = {'a': 123, 'b': 'xyz', 'c': 456}
        self.assertEqual(filter_dict(d, ()), {})
        self.assertEqual(filter_dict(d, ('a', 'c')), {'a': 123, 'c': 456})

    def test_get_cacheable(self):
        def calculate1():
            return "CALCULATED"

        self.assertEqual(get_cacheable('test_key:1', 60, calculate1), "CALCULATED")
        cache.set('test_key:1', json.dumps("CACHED"), 60)
        self.assertEqual(get_cacheable('test_key:1', 60, calculate1), "CACHED")

        # falsey values shouldn't trigger re-calculation
        cache.set('test_key:1', json.dumps(0), 60)
        self.assertEqual(get_cacheable('test_key:1', 60, calculate1), 0)

        def calculate2():
            return dict(a=123, b="abc")

        self.assertEqual(get_cacheable('test_key:2', 60, calculate2), dict(a=123, b="abc"))
        cache.set('test_key:2', '{"a":234,"b":"xyz"}', 60)
        self.assertEqual(get_cacheable('test_key:2', 60, calculate2), dict(a=234, b="xyz"))

    def test_get_obj_cacheable(self):
        def calculate():
            return "CALCULATED"

        self.assertEqual(get_obj_cacheable(self, '_test_value', calculate), "CALCULATED")
        self._test_value = "CACHED"
        self.assertEqual(get_obj_cacheable(self, '_test_value', calculate), "CACHED")

    def test_get_month_range(self):
        self.assertEqual(
            get_month_range(datetime(2014, 2, 10, 12, 30, 0, 0, pytz.timezone("Africa/Kigali"))),
            (datetime(2014, 2, 1, 0, 0, 0, 0, pytz.timezone("Africa/Kigali")),
             datetime(2014, 3, 1, 0, 0, 0, 0, pytz.timezone("Africa/Kigali"))))

    def test_chunks(self):
        self.assertEqual(list(chunks([], 2)), [])
        self.assertEqual(list(chunks([1, 2, 3, 4, 5], 2)), [[1, 2], [3, 4], [5]])
