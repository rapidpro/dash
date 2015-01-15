from __future__ import absolute_import, unicode_literals

from temba.types import Contact as TembaContact
from . import union


def temba_merge_contacts(first, second, primary_groups):
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

    # helper method to split contact groups into single primary and remaining secondary groups
    def split_groups(groups):
        primary, secondary = None, []
        for g in groups:
            if g in primary_groups:
                primary = g
            else:
                secondary.append(g)
        return primary, secondary

    # group merging honors given list of mutually exclusive primary groups
    first_primary_group, first_secondary_groups = split_groups(first.groups)
    second_primary_group, second_secondary_groups = split_groups(second.groups)
    primary_group = first_primary_group or second_primary_group
    merged_groups = union(first_secondary_groups, second_secondary_groups, [primary_group] if primary_group else [])

    return TembaContact.create(uuid=first.uuid, name=first.name,
                               urns=merged_urns, fields=merged_fields, groups=merged_groups)
