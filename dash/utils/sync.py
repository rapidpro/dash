from __future__ import absolute_import, unicode_literals
import logging

from enum import Enum
import six
from temba_client.types import Contact as TembaContact

from . import union, intersection, filter_dict


logger = logging.getLogger(__name__)


class ChangeType(Enum):
    created = 1
    updated = 2
    deleted = 3


def sync_push_contact(org, contact, change_type, mutex_group_sets):
    """
    Pushes a local change to a contact. mutex_group_sets is a list of UUID sets
    of groups whose membership is mutually exclusive. Contact class must define
    an as_temba instance method.
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
            merged_contact = temba_merge_contacts(
                local_contact, remote_contact, mutex_group_sets)

            # fetched contacts may have fields with null values but we can't
            # push these so we remove them
            merged_contact.fields = {k: v
                                     for k, v in six.iteritems(merged_contact.fields)
                                     if v is not None}

            client.update_contact(merged_contact.uuid,
                                  merged_contact.name,
                                  merged_contact.urns,
                                  merged_contact.fields,
                                  merged_contact.groups)

    elif change_type == ChangeType.deleted:
        client.delete_contact(contact.uuid)


def sync_pull_contacts(org, contact_class, fields=None, groups=None, last_time=None):
    """
    Pulls all contacts from RapidPro and syncs with local contacts. Contact
    class must define a class method called kwargs_from_temba which generates
    field kwargs from a fetched temba contact.

    :param org: the org
    :param contact_class: the contact class type
    :param fields: the contact field keys used - used to determine if local contact differs
    :param groups: the contact group UUIDs used - used to determine if local contact differs
    :return: tuple containing list of UUIDs for created, updated, deleted and failed contacts
    """
    # get all remote contacts
    client = org.get_temba_client()
    if last_time:
        updated_incoming_contacts = client.get_contacts(after=last_time)

    # get all existing contacts and organize by their UUID
    existing_contacts = contact_class.objects.filter(org=org)
    existing_by_uuid = {contact.uuid: contact for contact in existing_contacts}

    synced_uuids = set()

    created_uuids = []
    updated_uuids = []
    deleted_uuids = []
    failed_uuids = []

    for updated_incoming in updated_incoming_contacts:
        # ignore contacts with no URN
        if not updated_incoming.urns:
            logger.warning("Ignoring contact %s with no URN" % updated_incoming.uuid)
            failed_uuids.append(updated_incoming.uuid)
            continue

        if updated_incoming.uuid in existing_by_uuid:
            existing = existing_by_uuid[updated_incoming.uuid]

            diff = temba_compare_contacts(updated_incoming, existing.as_temba(), fields, groups)

            if diff or not existing.is_active:
                try:
                    kwargs = contact_class.kwargs_from_temba(org, updated_incoming)
                except ValueError:
                    failed_uuids.append(updated_incoming.uuid)
                    continue

                for field, value in six.iteritems(kwargs):
                    setattr(existing, field, value)

                existing.is_active = True
                existing.save()

                updated_uuids.append(updated_incoming.uuid)
        else:
            try:
                kwargs = contact_class.kwargs_from_temba(org, updated_incoming)
            except ValueError:
                failed_uuids.append(updated_incoming.uuid)
                continue

            contact_class.objects.create(**kwargs)
            created_uuids.append(kwargs['uuid'])

        synced_uuids.add(updated_incoming.uuid)

    # any existing contact not in all rapidpro contacts, is now deleted if not
    # already deleted
    incoming_contacts = client.get_contacts()
    incoming_uuids = [incoming.uuid for incoming in incoming_contacts]
    for existing_uuid, existing in six.iteritems(existing_by_uuid):
        if existing_uuid not in incoming_uuids and existing.is_active:
            deleted_uuids.append(existing_uuid)

    existing_contacts.filter(uuid__in=deleted_uuids).update(is_active=False)

    return created_uuids, updated_uuids, deleted_uuids, failed_uuids


def temba_compare_contacts(first, second, fields=None, groups=None):
    """
    Compares two Temba contacts to determine if there are differences. Returns
    first difference found.
    """
    if first.uuid != second.uuid:  # pragma: no cover
        raise ValueError("Can't compare contacts with different UUIDs")

    if first.name != second.name:
        return 'name'

    if sorted(first.urns) != sorted(second.urns):
        return 'urns'

    if groups is None and (sorted(first.groups) != sorted(second.groups)):
        return 'groups'
    if groups:
        a = sorted(intersection(first.groups, groups))
        b = sorted(intersection(second.groups, groups))
        if a != b:
            return 'groups'

    if fields is None and (first.fields != second.fields):
        return 'fields'
    if fields and (filter_dict(first.fields, fields) != filter_dict(second.fields, fields)):
        return 'fields'

    return None


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
    merged_urns = ['%s:%s' % (scheme, path) for scheme, path in six.iteritems(urns_by_scheme)]

    # fields are simple key based merge
    merged_fields = second.fields.copy()
    merged_fields.update(first.fields)

    # first merge mutually exclusive group sets
    first_groups = list(first.groups)
    second_groups = list(second.groups)
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
