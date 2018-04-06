from __future__ import unicode_literals


from dash.test import DashTest, MockClientQuery
from dash.utils import random_string
from dash.utils.sync import SyncOutcome, sync_from_remote, sync_local_to_set, sync_local_to_changes
from temba_client.v2.types import Contact as TembaContact
from .models import Contact, ContactSyncer, APIBackend


class SyncTest(DashTest):
    def setUp(self):
        super(SyncTest, self).setUp()

        self.unicef = self.create_org("UNICEF", 'Africa/Kampala', 'unicef')
        rapidpro_backend = self.unicef

        rapidpro_backend = self.unicef.backends.filter(slug='rapidpro').first()
        if not rapidpro_backend:
            rapidpro_backend, created = self.unicef.backends.get_or_create(api_token=random_string(32),
                                                                           slug='rapidpro',
                                                                           created_by=self.superuser,
                                                                           modified_by=self.superuser)
        self.rapidpro_backend = rapidpro_backend

        floip_backend = self.unicef.backends.filter(slug='floip').first()
        if not floip_backend:
            floip_backend, created = self.unicef.backends.get_or_create(api_token=random_string(32),
                                                                        slug='floip',
                                                                        created_by=self.superuser,
                                                                        modified_by=self.superuser)

        self.floip_backend = floip_backend

        self.joe = Contact.objects.create(org=self.unicef, uuid="C-001", name="Joe", backend=self.rapidpro_backend)
        self.joe2 = Contact.objects.create(org=self.unicef, uuid="CF-001", name="Joe", backend=self.floip_backend)
        self.syncer = ContactSyncer(backend=self.rapidpro_backend)
        self.syncer2 = ContactSyncer(backend=self.floip_backend)

    def test_get_backend(self):
        org_backend = self.unicef.backends.filter(slug="rapidpro").first()
        org_backend.host = 'http://example.com/'
        org_backend.backend_type = 'dash_test_runner.testapp.models.APIBackend'
        org_backend.save()

        self.assertIsInstance(self.unicef.get_backend(), APIBackend)

    def test_fetch_local(self):
        self.assertEqual(self.syncer.fetch_local(self.unicef, "C-001"), self.joe)
        self.assertEqual(self.syncer2.fetch_local(self.unicef, "CF-001"), self.joe2)

    def test_local_kwargs(self):
        remote = TembaContact.create(uuid="C-002", name="Frank", blocked=False)
        kwargs = self.syncer.local_kwargs(self.unicef, remote)
        self.assertEqual(kwargs, {'org': self.unicef, 'uuid': "C-002", 'name': "Frank",
                                  'backend': self.rapidpro_backend})

        remote = TembaContact.create(uuid="CF-002", name="Frank", blocked=False)
        kwargs = self.syncer2.local_kwargs(self.unicef, remote)
        self.assertEqual(kwargs, {'org': self.unicef, 'uuid': "CF-002", 'name': "Frank",
                                  'backend': self.floip_backend})

        remote = TembaContact.create(uuid="C-002", name="Frank", blocked=True)
        self.assertIsNone(self.syncer.local_kwargs(self.unicef, remote))

        remote = TembaContact.create(uuid="CF-002", name="Frank", blocked=True)
        self.assertIsNone(self.syncer2.local_kwargs(self.unicef, remote))

    def test_sync_from_remote(self):
        # no existing contact with same identity
        remote = TembaContact.create(uuid="C-002", name="Frank", blocked=False)
        self.assertEqual(sync_from_remote(self.unicef, self.syncer, remote), SyncOutcome.created)

        Contact.objects.get(org=self.unicef, uuid="C-002", name="Frank", backend=self.rapidpro_backend, is_active=True)
        self.assertIsNone(Contact.objects.filter(org=self.unicef, uuid="C-002", name="Frank",
                                                 backend=self.floip_backend, is_active=True).first())

        remote = TembaContact.create(uuid="CF-002", name="Frank", blocked=False)
        self.assertEqual(sync_from_remote(self.unicef, self.syncer2, remote), SyncOutcome.created)
        Contact.objects.get(org=self.unicef, uuid="CF-002", name="Frank", backend=self.floip_backend, is_active=True)

        # no significant change
        remote = TembaContact.create(uuid="C-002", name="Frank", blocked=False)
        self.assertEqual(sync_from_remote(self.unicef, self.syncer, remote), SyncOutcome.ignored)

        Contact.objects.get(org=self.unicef, uuid="C-002", name="Frank", backend=self.rapidpro_backend, is_active=True)

        # significant change (name)
        remote = TembaContact.create(uuid="C-002", name="Franky", blocked=False)
        self.assertEqual(sync_from_remote(self.unicef, self.syncer, remote), SyncOutcome.updated)

        Contact.objects.get(org=self.unicef, uuid="C-002", name="Franky", backend=self.rapidpro_backend, is_active=True)

        # change to something we don't want locally
        remote = TembaContact.create(uuid="C-002", name="Franky", blocked=True)
        self.assertEqual(sync_from_remote(self.unicef, self.syncer, remote), SyncOutcome.deleted)

        Contact.objects.get(org=self.unicef, uuid="C-002", name="Franky", backend=self.rapidpro_backend,
                            is_active=False)

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

        remote_set = [
            # first contact removed
            TembaContact.create(uuid="CF-002", name="Bob", blocked=False),    # no change
            TembaContact.create(uuid="CF-003", name="Colm", blocked=False),   # changed name
            TembaContact.create(uuid="CF-005", name="Edward", blocked=False)  # new contact
        ]
        self.assertEqual(sync_local_to_set(self.unicef, self.syncer2, remote_set), (3, 0, 0, 0))
        self.assertEqual(Contact.objects.count(), 7)
        Contact.objects.get(org=self.unicef, uuid="CF-002", name="Bob", backend=self.floip_backend, is_active=True)
        Contact.objects.get(org=self.unicef, uuid="CF-003", name="Colm", backend=self.floip_backend, is_active=True)
        Contact.objects.get(org=self.unicef, uuid="CF-005", name="Edward", backend=self.floip_backend, is_active=True)

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

        fetches = MockClientQuery([
            TembaContact.create(uuid="CF-001", name="Anne", blocked=False),
            TembaContact.create(uuid="CF-002", name="Bob", blocked=False),
            TembaContact.create(uuid="CF-003", name="Colin", blocked=False),
            TembaContact.create(uuid="CF-004", name="Donald", blocked=True)
        ])
        deleted_fetches = MockClientQuery([])  # no deleted contacts this time

        self.assertEqual(sync_local_to_changes(self.unicef, self.syncer2, fetches, deleted_fetches), (3, 0, 0, 1))

        fetches = MockClientQuery([
            TembaContact.create(uuid="CF-005", name="Edward", blocked=False),  # new contact
            TembaContact.create(uuid="CF-006", name="Frank", blocked=False),   # new contact
        ])
        deleted_fetches = MockClientQuery([
            TembaContact.create(uuid="CF-001", name=None, blocked=None),       # deleted
        ])

        self.assertEqual(sync_local_to_changes(self.unicef, self.syncer2, fetches, deleted_fetches), (2, 0, 1, 0))

        fetches = MockClientQuery([
            TembaContact.create(uuid="CF-002", name="Bob", blocked=True),   # blocked so locally invalid
            TembaContact.create(uuid="CF-003", name="Colm", blocked=False),  # changed name
        ])
        deleted_fetches = MockClientQuery([])

        self.assertEqual(sync_local_to_changes(self.unicef, self.syncer2, fetches, deleted_fetches), (0, 1, 1, 0))
