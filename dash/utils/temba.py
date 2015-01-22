from __future__ import absolute_import, unicode_literals

from enum import Enum
from temba.types import Contact as TembaContact
from . import union, intersection


class ChangeType(Enum):
    created = 1
    updated = 2
    deleted = 3


def temba_compare_contacts(first, second):
    """
    Compares two Temba contacts to determine if there are differences
    """
    if first.uuid != second.uuid:  # pragma: no cover
        raise ValueError("Can't compare contacts with different UUIDs")

    return first.name != second.name or sorted(first.urns) != sorted(second.urns) or first.fields != second.fields or sorted(first.groups) != sorted(second.groups)


def temba_push_contact(org, contact, change_type, mutex_group_sets):
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
