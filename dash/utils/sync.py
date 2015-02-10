from __future__ import absolute_import, unicode_literals

import logging

from collections import defaultdict
from enum import Enum
from temba.types import Contact as TembaContact
from . import union, intersection, filter_dict


logger = logging.getLogger(__name__)


class ChangeType(Enum):
    created = 1
    updated = 2
    deleted = 3


def sync_push_contact(org, contact, change_type, mutex_group_sets):
    """
    Pushes a local change to a contact. mutex_group_sets is a list of UUID sets of groups whose membership is mutually
    exclusive. Contact class must define an as_temba instance method.
    """
    client = org.get_temba_client()

    if change_type == ChangeType.created:
        temba_contact = contact.as_temba()
        temba_contact = client.create_contact(temba_contact.name,
                                              temba_contact.urns,
                                              temba_contact.fields,
                                              temba_contact.groups)
        # update our contact with the new UUID from RapidPro
        contact.uuid = temba_contact.uuid
        contact.save()

    elif change_type == ChangeType.updated:
        # fetch contact so that we can merge with its URNs, fields and groups
        remote_contact = client.get_contact(contact.uuid)
        local_contact = contact.as_temba()

        if temba_compare_contacts(remote_contact, local_contact):
            merged_contact = temba_merge_contacts(local_contact, remote_contact, mutex_group_sets)

            client.update_contact(merged_contact.uuid,
                                  merged_contact.name,
                                  merged_contact.urns,
                                  merged_contact.fields,
                                  merged_contact.groups)

    elif change_type == ChangeType.deleted:
        client.delete_contact(contact.uuid)


def sync_pull_contacts(org, primary_groups, contact_class, contact_fields=None):
    """
    Pulls contacts from RapidPro and syncs with local contacts. Contact class must define a classmethod called
    kwargs_from_temba which generates field kwargs from a fetched temba contact.
    """
    client = org.get_temba_client()

    # get all existing contacts and organize by their UUID
    existing_contacts = contact_class.objects.filter(org=org)
    existing_by_uuid = {contact.uuid: contact for contact in existing_contacts}

    # get all remote contacts in our primary groups
    incoming_contacts = client.get_contacts(groups=primary_groups)

    # organize incoming contacts by the UUID of their primary group
    incoming_by_primary = defaultdict(list)
    incoming_uuids = set()
    for incoming_contact in incoming_contacts:
        # ignore contacts with no URN
        if not incoming_contact.urns:
            logger.warning("Ignoring contact %s with no URN" % incoming_contact.uuid)
            continue

        # which primary groups is this contact in?
        contact_primary_groups = intersection(incoming_contact.groups, primary_groups)

        if len(contact_primary_groups) != 1:
            logger.warning("Ignoring contact %s who is in multiple primary groups" % incoming_contact.uuid)
            continue

        incoming_by_primary[contact_primary_groups[0]].append(incoming_contact)
        incoming_uuids.add(incoming_contact.uuid)

    created_uuids = []
    updated_uuids = []
    deleted_uuids = []

    for primary_group in primary_groups:
        incoming_contacts = incoming_by_primary[primary_group]

        for incoming in incoming_contacts:
            if incoming.uuid in existing_by_uuid:
                existing = existing_by_uuid[incoming.uuid]

                if temba_compare_contacts(incoming, existing.as_temba(), contact_fields) or not existing.is_active:
                    kwargs = contact_class.kwargs_from_temba(org, incoming)
                    for field, value in kwargs.iteritems():
                        setattr(existing, field, value)

                    existing.is_active = True
                    existing.save()

                    updated_uuids.append(incoming.uuid)
            else:
                kwargs = contact_class.kwargs_from_temba(org, incoming)
                contact_class.objects.create(**kwargs)
                created_uuids.append(kwargs['uuid'])

    # any existing contact not in the incoming set, is now deleted if not already deleted
    for existing_uuid, existing in existing_by_uuid.iteritems():
        if existing_uuid not in incoming_uuids and existing.is_active:
            deleted_uuids.append(existing_uuid)

    existing_contacts.filter(uuid__in=deleted_uuids).update(is_active=False)

    return created_uuids, updated_uuids, deleted_uuids


def temba_compare_contacts(first, second, fields=None):
    """
    Compares two Temba contacts to determine if there are differences
    """
    if first.uuid != second.uuid:  # pragma: no cover
        raise ValueError("Can't compare contacts with different UUIDs")

    if first.name != second.name:
        return True

    if sorted(first.urns) != sorted(second.urns):
        return True

    if sorted(first.groups) != sorted(second.groups):
        return True

    if fields is None and (first.fields != second.fields):
        return True
    if fields and (filter_dict(first.fields, fields) != filter_dict(second.fields, fields)):
        return True

    return False


def temba_merge_contacts(first, second, mutex_group_sets):
    """
    Merges two Temba contacts, with priority given to the first contact
    """
    if first.uuid != second.uuid:  # pragma: no cover
        raise ValueError("Can't merge contacts with different UUIDs")

    # URNs are merged by scheme
    first_urns_by_scheme = {u[0]: u[1] for u in [urn.split(':', 1) for urn in first.urns]}
    urns_by_scheme = {u[0]: u[1] for u in [urn.split(':', 1) for urn in second.urns]}
    urns_by_scheme.update(first_urns_by_scheme)
    merged_urns = ['%s:%s' % (scheme, path) for scheme, path in urns_by_scheme.iteritems()]

    # fields are simple key based merge
    merged_fields = second.fields.copy()
    merged_fields.update(first.fields)

    # first merge mutually exclusive group sets
    first_groups = set(first.groups)
    second_groups = set(second.groups)
    merged_mutex_groups = []
    for group_set in mutex_group_sets:
        from_first = intersection(first_groups, group_set)
        if from_first:
            merged_mutex_groups.append(from_first[0])
        else:
            from_second = intersection(second_groups, group_set)
            if from_second:
                merged_mutex_groups.append(from_second[0])

        for group in group_set:
            if group in first_groups:
                first_groups.remove(group)
            if group in second_groups:
                second_groups.remove(group)

    # then merge the remaining groups
    merged_groups = merged_mutex_groups + union(first_groups, second_groups)

    return TembaContact.create(uuid=first.uuid, name=first.name,
                               urns=merged_urns, fields=merged_fields, groups=merged_groups)
