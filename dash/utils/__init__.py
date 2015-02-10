from __future__ import absolute_import, unicode_literals

import random


def intersection(*args):
    """
    Return the intersection of lists
    """
    if not args:
        return []

    return list(set(args[0]).intersection(*args[1:]))


def union(*args):
    """
    Return the union of lists
    """
    if not args:
        return []

    return list(set(args[0]).union(*args[1:]))


def random_string(length):
    """
    Generates a random alphanumeric string
    """
    letters = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # avoid things that could be mistaken ex: 'I' and '1'
    return ''.join([random.choice(letters) for _ in range(length)])


def filter_dict(d, keys):
    """
    Creates a new dict from an existing dict that only has the given keys
    """
    return {k: v for k, v in d.iteritems() if k in keys}
