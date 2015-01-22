from __future__ import absolute_import, unicode_literals

import datetime
import pytz

from django.utils import timezone
from django.test import TestCase
from temba.types import Contact as TembaContact
from .temba import temba_compare_contacts, temba_merge_contacts
from . import format_iso8601, parse_iso8601, intersection, union, random_string


class InitTest(TestCase):
    class TestTZ(datetime.tzinfo):
        def utcoffset(self, dt):
            return datetime.timedelta(hours=-5)

    def test_format_iso8601(self):
        d = datetime.datetime(2014, 1, 2, 3, 4, 5, 6, InitTest.TestTZ())
        self.assertEqual(format_iso8601(d), '2014-01-02T08:04:05.000006Z')

    def test_parse_iso8601(self):
        d = datetime.datetime(2014, 1, 2, 3, 4, 5, 6, pytz.UTC)
        self.assertEqual(parse_iso8601('2014-01-02T03:04:05.000006Z'), d)

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
        self.assertEquals(1000, len(rs))
        self.assertFalse('1' in rs or 'I' in rs or '0' in rs or 'O' in rs)


class TembaTest(TestCase):
    def test_compare_contacts(self):
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

    def test_merge_contacts(self):
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
