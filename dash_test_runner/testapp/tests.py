from __future__ import unicode_literals


from dash.test import DashTest, MockClientQuery
from dash.utils.sync import SyncOutcome, sync_from_remote, sync_local_to_set, sync_local_to_changes
from temba_client.v2.types import Contact as TembaContact
from .models import Contact, ContactSyncer


class SyncTest(DashTest):
    def setUp(self):
        super(SyncTest, self).setUp()

        self.unicef = self.create_org("UNICEF", 'Africa/Kampala', 'unicef')
        self.joe = Contact.objects.create(org=self.unicef, uuid="C-001", name="Joe")
        self.syncer = ContactSyncer()

    def test_fetch_local(self):
        self.assertEqual(self.syncer.fetch_local(self.unicef, "C-001"), self.joe)

    def test_local_kwargs(self):
        remote = TembaContact.create(uuid="C-002", name="Frank", blocked=False)
        kwargs = self.syncer.local_kwargs(self.unicef, remote)
        self.assertEqual(kwargs, {'org': self.unicef, 'uuid': "C-002", 'name': "Frank"})

        remote = TembaContact.create(uuid="C-002", name="Frank", blocked=True)
        self.assertIsNone(self.syncer.local_kwargs(self.unicef, remote))

    def test_sync_from_remote(self):
        # no existing contact with same identity
        remote = TembaContact.create(uuid="C-002", name="Frank", blocked=False)
        self.assertEqual(sync_from_remote(self.unicef, self.syncer, remote), SyncOutcome.created)

        Contact.objects.get(org=self.unicef, uuid="C-002", name="Frank", is_active=True)

        # no significant change
        remote = TembaContact.create(uuid="C-002", name="Frank", blocked=False)
        self.assertEqual(sync_from_remote(self.unicef, self.syncer, remote), SyncOutcome.ignored)

        Contact.objects.get(org=self.unicef, uuid="C-002", name="Frank", is_active=True)

        # significant change (name)
        remote = TembaContact.create(uuid="C-002", name="Franky", blocked=False)
        self.assertEqual(sync_from_remote(self.unicef, self.syncer, remote), SyncOutcome.updated)

        Contact.objects.get(org=self.unicef, uuid="C-002", name="Franky", is_active=True)

        # change to something we don't want locally
        remote = TembaContact.create(uuid="C-002", name="Franky", blocked=True)
        self.assertEqual(sync_from_remote(self.unicef, self.syncer, remote), SyncOutcome.deleted)

        Contact.objects.get(org=self.unicef, uuid="C-002", name="Franky", is_active=False)

    def test_sync_local_to_set(self):
        Contact.objects.all().delete()  # start with no contacts...

        remote_set = [
            TembaContact.create(uuid="C-001", name="Anne", blocked=False),
            TembaContact.create(uuid="C-002", name="Bob", blocked=False),
            TembaContact.create(uuid="C-003", name="Colin", blocked=False),
            TembaContact.create(uuid="C-004", name="Donald", blocked=True)
        ]

        self.assertEqual(sync_local_to_set(self.unicef, self.syncer, remote_set), (3, 0, 0, 1))
        self.assertEqual(Contact.objects.count(), 3)

        remote_set = [
            # first contact removed
            TembaContact.create(uuid="C-002", name="Bob", blocked=False),    # no change
            TembaContact.create(uuid="C-003", name="Colm", blocked=False),   # changed name
            TembaContact.create(uuid="C-005", name="Edward", blocked=False)  # new contact
        ]

        self.assertEqual(sync_local_to_set(self.unicef, self.syncer, remote_set), (1, 1, 1, 1))

        self.assertEqual(Contact.objects.count(), 4)
        Contact.objects.get(org=self.unicef, uuid="C-001", name="Anne", is_active=False)
        Contact.objects.get(org=self.unicef, uuid="C-002", name="Bob", is_active=True)
        Contact.objects.get(org=self.unicef, uuid="C-003", name="Colm", is_active=True)
        Contact.objects.get(org=self.unicef, uuid="C-005", name="Edward", is_active=True)

    def test_sync_local_to_changes(self):
        Contact.objects.all().delete()  # start with no contacts...

        fetches = MockClientQuery([
            TembaContact.create(uuid="C-001", name="Anne", blocked=False),
            TembaContact.create(uuid="C-002", name="Bob", blocked=False),
            TembaContact.create(uuid="C-003", name="Colin", blocked=False),
            TembaContact.create(uuid="C-004", name="Donald", blocked=True)
        ])
        deleted_fetches = MockClientQuery([])  # no deleted contacts this time

        self.assertEqual(sync_local_to_changes(self.unicef, self.syncer, fetches, deleted_fetches), (3, 0, 0, 1))

        fetches = MockClientQuery([
            TembaContact.create(uuid="C-005", name="Edward", blocked=False),  # new contact
            TembaContact.create(uuid="C-006", name="Frank", blocked=False),   # new contact
        ])
        deleted_fetches = MockClientQuery([
            TembaContact.create(uuid="C-001", name=None, blocked=None),       # deleted
        ])

        self.assertEqual(sync_local_to_changes(self.unicef, self.syncer, fetches, deleted_fetches), (2, 0, 1, 0))

        fetches = MockClientQuery([
            TembaContact.create(uuid="C-002", name="Bob", blocked=True),   # blocked so locally invalid
            TembaContact.create(uuid="C-003", name="Colm", blocked=False),  # changed name
        ])
        deleted_fetches = MockClientQuery([])

        self.assertEqual(sync_local_to_changes(self.unicef, self.syncer, fetches, deleted_fetches), (0, 1, 1, 0))
