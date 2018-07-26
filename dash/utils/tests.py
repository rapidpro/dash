import json
from datetime import datetime
from itertools import chain

import pytz

from django.core.cache import cache

from . import (
    chunks,
    datetime_to_ms,
    filter_dict,
    get_cacheable,
    get_month_range,
    get_obj_cacheable,
    intersection,
    is_dict_equal,
    ms_to_datetime,
    random_string,
    union,
)
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
        self.assertFalse("1" in rs or "I" in rs or "0" in rs or "O" in rs)

    def test_filter_dict(self):
        d = {"a": 123, "b": "xyz", "c": 456}
        self.assertEqual(filter_dict(d, ()), {})
        self.assertEqual(filter_dict(d, ("a", "c")), {"a": 123, "c": 456})

    def test_get_cacheable(self):
        def calculate1():
            return "CALCULATED"

        self.assertEqual(get_cacheable("test_key:1", 60, calculate1), "CALCULATED")
        cache.set("test_key:1", json.dumps("CACHED"), 60)
        self.assertEqual(get_cacheable("test_key:1", 60, calculate1), "CACHED")
        self.assertEqual(get_cacheable("test_key:1", 60, calculate1, recalculate=True), "CALCULATED")

        # falsey values shouldn't trigger re-calculation
        cache.set("test_key:1", json.dumps(0), 60)
        self.assertEqual(get_cacheable("test_key:1", 60, calculate1), 0)

        def calculate2():
            return dict(a=123, b="abc")

        self.assertEqual(get_cacheable("test_key:2", 60, calculate2), dict(a=123, b="abc"))
        cache.set("test_key:2", '{"a":234,"b":"xyz"}', 60)
        self.assertEqual(get_cacheable("test_key:2", 60, calculate2), dict(a=234, b="xyz"))

    def test_get_obj_cacheable(self):
        def calculate():
            return "CALCULATED"

        self.assertEqual(get_obj_cacheable(self, "_test_value", calculate), "CALCULATED")
        self._test_value = "CACHED"
        self.assertEqual(get_obj_cacheable(self, "_test_value", calculate), "CACHED")
        self.assertEqual(get_obj_cacheable(self, "_test_value", calculate, recalculate=True), "CALCULATED")

    def test_datetime_to_ms(self):
        d1 = datetime(2014, 1, 2, 3, 4, 5, 678900, tzinfo=pytz.utc)
        self.assertEqual(datetime_to_ms(d1), 1388631845678)  # from http://unixtimestamp.50x.eu

        # conversion to millis loses some accuracy
        self.assertEqual(ms_to_datetime(1388631845678), datetime(2014, 1, 2, 3, 4, 5, 678000, tzinfo=pytz.utc))

        tz = pytz.timezone("Africa/Kigali")
        d2 = tz.localize(datetime(2014, 1, 2, 3, 4, 5, 600000))
        self.assertEqual(datetime_to_ms(d2), 1388624645600)
        self.assertEqual(ms_to_datetime(1388624645600), d2.astimezone(pytz.utc))

    def test_get_month_range(self):
        self.assertEqual(
            get_month_range(datetime(2014, 2, 10, 12, 30, 0, 0, pytz.timezone("Africa/Kigali"))),
            (
                datetime(2014, 2, 1, 0, 0, 0, 0, pytz.timezone("Africa/Kigali")),
                datetime(2014, 3, 1, 0, 0, 0, 0, pytz.timezone("Africa/Kigali")),
            ),
        )

    def test_chunks(self):
        self.assertEqual(list(chunks([], 2)), [])
        self.assertEqual(list(chunks([1, 2, 3, 4, 5], 2)), [[1, 2], [3, 4], [5]])

        # if data is a set, chunking still works but with non-deterministic ordering
        batches = list(chunks({1, 2, 3, 4, 5}, 2))
        self.assertEqual(len(batches), 3)
        self.assertEqual(set(chain(*batches)), {1, 2, 3, 4, 5})

    def test_is_dict_equal(self):
        self.assertTrue(is_dict_equal({"a": 1, "b": 2}, {"b": 2, "a": 1}))
        self.assertFalse(is_dict_equal({"a": 1, "b": 2}, {"a": 1, "b": 3}))
        self.assertFalse(is_dict_equal({"a": 1, "b": 2}, {"a": 1, "c": 2}))
        self.assertFalse(is_dict_equal({"a": 1, "b": 2}, {"a": 1, "b": 2, "c": 3}))

        self.assertTrue(is_dict_equal({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 2, "c": 4}, keys=("a", "b")))

        self.assertTrue(is_dict_equal({"a": 1, "b": 2}, {"a": 1, "b": 2, "c": None}, ignore_none_values=True))
        self.assertFalse(is_dict_equal({"a": 1, "b": 2}, {"a": 1, "b": 2, "c": None}, ignore_none_values=False))
