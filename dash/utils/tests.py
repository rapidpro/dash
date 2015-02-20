from __future__ import absolute_import, unicode_literals

import json
import pytz

from datetime import datetime
from django.core.cache import cache
from django.utils import timezone
from django.test import TestCase
from temba.types import Contact as TembaContact
from . import intersection, union, random_string, filter_dict, get_cacheable, get_obj_cacheable, get_month_range
from .sync import temba_compare_contacts, temba_merge_contacts


class InitTest(TestCase):
    def test_intersection(self):
        self.assertEqual(intersection(), [])
        self.assertEqual(intersection([1]), [1])
        self.assertEqual(sorted(intersection([1, 2, 3], [2, 3, 4])), [2, 3])

    def test_union(self):
        self.assertEqual(union(), [])
        self.assertEqual(union([1]), [1])
        self.assertEqual(sorted(union([1, 2, 3], [2, 3, 4])), [1, 2, 3, 4])

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
        self.assertEqual(get_month_range(datetime(2014, 2, 10, 12, 30, 0, 0, pytz.timezone("Africa/Kigali"))),
                         (datetime(2014, 2, 1, 0, 0, 0, 0, pytz.timezone("Africa/Kigali")),
                          datetime(2014, 3, 1, 0, 0, 0, 0, pytz.timezone("Africa/Kigali"))))


class SyncTest(TestCase):
    def test_temba_compare_contacts(self):
        # no differences
        first = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-001'],
                                    fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-001'],
                                     fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        self.assertIsNone(temba_compare_contacts(first, second))
        self.assertIsNone(temba_compare_contacts(second, first))

        # different name
        second = TembaContact.create(uuid='000-001', name="Annie", urns=['tel:1234'], groups=['000-001'],
                                     fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        self.assertEqual(temba_compare_contacts(first, second), 'name')

        # different URNs
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234', 'twitter:ann'], groups=['000-001'],
                                     fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        self.assertEqual(temba_compare_contacts(first, second), 'urns')

        # different group
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-002'],
                                     fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        self.assertEqual(temba_compare_contacts(first, second), 'groups')
        self.assertEqual(temba_compare_contacts(first, second, groups=('000-001', '000-002')), 'groups')
        self.assertIsNone(temba_compare_contacts(first, second, groups=()))
        self.assertIsNone(temba_compare_contacts(first, second, groups=('000-003', '000-004')))

        # different field
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-001'],
                                     fields=dict(chat_name="annie"), language='eng', modified_on=timezone.now())
        self.assertEqual(temba_compare_contacts(first, second), 'fields')
        self.assertEqual(temba_compare_contacts(first, second, fields=('chat_name', 'gender')), 'fields')
        self.assertIsNone(temba_compare_contacts(first, second, fields=()))
        self.assertIsNone(temba_compare_contacts(first, second, fields=('age', 'gender')))

        # additional field
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-001'],
                                     fields=dict(chat_name="ann", age=18), language='eng', modified_on=timezone.now())
        self.assertEqual(temba_compare_contacts(first, second), 'fields')
        self.assertIsNone(temba_compare_contacts(first, second, fields=()))
        self.assertIsNone(temba_compare_contacts(first, second, fields=('chat_name',)))

    def test_temba_merge_contacts(self):
        contact1 = TembaContact.create(uuid="000-001", name="Bob",
                                       urns=['tel:123', 'email:bob@bob.com'],
                                       fields=dict(chat_name="bob", age=23),
                                       groups=['000-001', '000-002', '000-010'])
        contact2 = TembaContact.create(uuid="000-001", name="Bobby",
                                       urns=['tel:234', 'twitter:bob'],
                                       fields=dict(chat_name="bobz", state='IN'),
                                       groups=['000-003', '000-009', '000-011'])

        merged = temba_merge_contacts(contact1, contact2, mutex_group_sets=(('000-001', '000-002', '000-003'),
                                                                            ('000-008', '000-009'),
                                                                            ('000-098', '000-099')))
        self.assertEqual(merged.uuid, '000-001')
        self.assertEqual(merged.name, "Bob")
        self.assertEqual(sorted(merged.urns), ['email:bob@bob.com', 'tel:123', 'twitter:bob'])
        self.assertEqual(merged.fields, dict(chat_name="bob", age=23, state='IN'))
        self.assertEqual(sorted(merged.groups), ['000-001', '000-009', '000-010', '000-011'])
