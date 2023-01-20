import time
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Optional, Tuple

"""
Sync support
"""


class SyncOutcome(Enum):
    created = 1
    updated = 2
    deleted = 3
    ignored = 4


class BaseSyncer(object, metaclass=ABCMeta):
    """
    Base class for classes that describe how to synchronize particular local models against incoming data
    """

    model = None
    local_id_attr = "uuid"
    remote_id_attr = "uuid"
    select_related = ()
    prefetch_related = ()
    local_backend_attr = None

    def __init__(self, backend):
        self.backend = backend

    def identify_local(self, local):
        """
        Gets the unique identity of the local model instance
        :param local: the local model instance
        :return: the unique identity
        """
        return getattr(local, self.local_id_attr)

    def identify_remote(self, remote):
        """
        Gets the unique identity of the remote object
        :param remote: the remote object
        :return: the unique identity
        """
        return getattr(remote, self.remote_id_attr)

    def lock(self, org, identity):
        """
        Gets a lock on the given identity value
        :param org: the org
        :param identity: the unique identity
        :return: the lock
        """
        return self.model.lock(org, identity)

    def fetch_local(self, org, identity):
        """
        Fetches the local model instance with the given identity, returning none if it doesn't exist
        :param org: the org
        :param identity: the unique identity
        :return: the instance or none
        """
        qs = self.fetch_all(org=org).filter(**{self.local_id_attr: identity})

        if self.select_related:
            qs = qs.select_related(*self.select_related)
        if self.prefetch_related:
            qs = qs.prefetch_related(*self.prefetch_related)

        return qs.first()

    def fetch_all(self, org):
        """
        Fetches all local objects
        :param org: the org
        :return: the queryset
        """
        qs = self.model.objects.filter(org=org)
        if self.local_backend_attr is not None:
            qs = qs.filter(**{self.local_backend_attr: self.backend})
        return qs

    @abstractmethod
    def local_kwargs(self, org, remote):
        """
        Generates kwargs for creating or updating a local model instance from a remote object. Returning none from this
        method means that the remote object doesn't belong locally.
        :param org: the org
        :param remote: the incoming remote object
        :return: the kwargs or none
        """
        pass

    def update_required(self, local, remote, remote_as_kwargs):
        """
        Determines whether local instance differs from the remote object and so needs to be updated. By default this
        will always update the local instance which is obviously inefficient.
        :param local: the local instance
        :param remote: the incoming remote object
        :param remote_as_kwargs: the generated kwargs from remote object
        :return: whether the local instance must be updated
        """
        return True

    def delete_local(self, local):
        """
        Deletes a local instance
        :param local:
        :return:
        """
        local.is_active = False
        local.save(update_fields=("is_active",))

    def create_local(self, remote_as_kwargs):
        """
        Create a local instance
        :param remote_as_kwargs: the generated kwargs from remote object
        :return: the created instance
        """
        return self.model.objects.create(**remote_as_kwargs)

    def update_local(self, local, remote_as_kwargs):
        """
        Update a local instance
        :param local: the local instance
        :param remote_as_kwargs: the generated kwargs from remote object
        :return: the updated instance
        """
        for field, value in remote_as_kwargs.items():
            setattr(local, field, value)
        local.is_active = True
        local.save()
        return local


def sync_from_remote(org, syncer, remote):
    """
    Sync local instance against a single remote object

    :param * org: the org
    :param * syncer: the local model syncer
    :param * remote: the remote object
    :return: the outcome (created, updated or deleted)
    """
    identity = syncer.identify_remote(remote)

    with syncer.lock(org, identity):
        existing = syncer.fetch_local(org, identity)

        # derive kwargs for the local model (none return here means don't keep)
        remote_as_kwargs = syncer.local_kwargs(org, remote)

        # exists locally
        if existing:
            existing.org = org  # saves pre-fetching since we already have the org

            if remote_as_kwargs:
                if syncer.update_required(existing, remote, remote_as_kwargs) or not existing.is_active:
                    syncer.update_local(existing, remote_as_kwargs)
                    return SyncOutcome.updated

            elif existing.is_active:  # exists locally, but shouldn't now to due to model changes
                syncer.delete_local(existing)
                return SyncOutcome.deleted

        elif remote_as_kwargs:
            syncer.create_local(remote_as_kwargs)
            return SyncOutcome.created

    return SyncOutcome.ignored


def sync_local_to_set(org, syncer, remote_set) -> dict:
    """
    Syncs an org's set of local instances of a model to match the set of remote objects. Local objects not in the remote
    set are deleted.

    :param org: the org
    :param * syncer: the local model syncer
    :param remote_set: the set of remote objects
    :return: dict of counts of created, updated, deleted, ignored local instances
    """
    outcome_counts = {SyncOutcome.created: 0, SyncOutcome.updated: 0, SyncOutcome.deleted: 0, SyncOutcome.ignored: 0}

    remote_identities = set()

    for remote in remote_set:
        outcome = sync_from_remote(org, syncer, remote)
        outcome_counts[outcome] += 1

        remote_identities.add(syncer.identify_remote(remote))

    # active local objects which weren't in the remote set need to be deleted
    active_locals = syncer.fetch_all(org).filter(is_active=True)
    delete_locals = active_locals.exclude(**{syncer.local_id_attr + "__in": remote_identities})

    for local in delete_locals:
        with syncer.lock(org, syncer.identify_local(local)):
            syncer.delete_local(local)
            outcome_counts[SyncOutcome.deleted] += 1

    return outcome_counts


def sync_local_to_changes(
    org, syncer, fetches, deleted_fetches, progress_callback=None, time_limit: int = None
) -> Tuple[dict, Optional[str]]:
    """
    Sync local instances against iterators which return fetches of changed and deleted remote objects.

    :param * org: the org
    :param * syncer: the local model syncer
    :param * fetches: an iterator returning fetches of modified remote objects
    :param * deleted_fetches: an iterator returning fetches of deleted remote objects
    :param * progress_callback: callable for tracking progress - called for each fetch with number of contacts fetched
    :param * time_limit: number of seconds to limit fetching too (optional)
    :return: tuple of a dict of counts of created, updated, deleted, ignored local instances and a possible cursor if
             fetching didn't complete
    """
    num_synced = 0
    outcome_counts = {SyncOutcome.created: 0, SyncOutcome.updated: 0, SyncOutcome.deleted: 0, SyncOutcome.ignored: 0}
    resume_cursor = None

    start = time.time()

    for fetch in fetches:
        for remote in fetch:
            outcome = sync_from_remote(org, syncer, remote)
            outcome_counts[outcome] += 1

        num_synced += len(fetch)
        if progress_callback:
            progress_callback(num_synced)

        if time_limit and time.time() - start > time_limit:
            resume_cursor = fetches.get_cursor()
            break

    # any item that has been deleted remotely should also be released locally
    for deleted_fetch in deleted_fetches:
        for deleted_remote in deleted_fetch:
            identity = syncer.identify_remote(deleted_remote)
            with syncer.lock(org, identity):
                existing = syncer.fetch_local(org, identity)
                if existing:
                    syncer.delete_local(existing)
                    outcome_counts[SyncOutcome.deleted] += 1

        num_synced += len(deleted_fetch)
        if progress_callback:
            progress_callback(num_synced)

    return outcome_counts, resume_cursor
