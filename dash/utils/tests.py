from __future__ import absolute_import, unicode_literals

from django.utils import timezone
from django.test import TestCase
from temba.types import Contact as TembaContact
from . import intersection, union, random_string, filter_dict, get_obj_cacheable
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

    def test_get_obj_cacheable(self):
        def calculate():
            return "CALCULATED"

        self.assertEqual(get_obj_cacheable(self, '_test_value', calculate), "CALCULATED")
        self._test_value = "CACHED"
        self.assertEqual(get_obj_cacheable(self, '_test_value', calculate), "CACHED")


class SyncTest(TestCase):
    def test_temba_compare_contacts(self):
        # no differences
        first = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-001'],
                                    fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-001'],
                                     fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        self.assertFalse(temba_compare_contacts(first, second))
        self.assertFalse(temba_compare_contacts(second, first))

        # different name
        second = TembaContact.create(uuid='000-001', name="Annie", urns=['tel:1234'], groups=['000-001'],
                                     fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        self.assertTrue(temba_compare_contacts(first, second))

        # different URNs
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234', 'twitter:ann'], groups=['000-001'],
                                     fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        self.assertTrue(temba_compare_contacts(first, second))

        # different group
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-002'],
                                     fields=dict(chat_name="ann"), language='eng', modified_on=timezone.now())
        self.assertTrue(temba_compare_contacts(first, second))

        # different field
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-001'],
                                     fields=dict(chat_name="annie"), language='eng', modified_on=timezone.now())
        self.assertTrue(temba_compare_contacts(first, second))

        # additional field
        second = TembaContact.create(uuid='000-001', name="Ann", urns=['tel:1234'], groups=['000-001'],
                                     fields=dict(chat_name="ann", age=18), language='eng', modified_on=timezone.now())
        self.assertTrue(temba_compare_contacts(first, second))
        self.assertTrue(temba_compare_contacts(first, second, None))
        self.assertFalse(temba_compare_contacts(first, second, ()))
        self.assertFalse(temba_compare_contacts(first, second, ('chat_name',)))

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
