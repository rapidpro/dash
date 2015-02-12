from __future__ import absolute_import, unicode_literals

import calendar
import datetime
import json
import pytz
import random

from django.core.cache import cache


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


def get_obj_cacheable(obj, obj_attr, calculate):
    """
    Gets the result of a method call, using the given object and attribute name as a cache
    """
    if hasattr(obj, obj_attr):
        return getattr(obj, obj_attr)

    calculated = calculate()
    setattr(obj, obj_attr, calculated)

    return calculated


def get_sys_cacheable(key, ttl, calculate, as_json=True):
    """
    Gets the result of a method call, using the given key and TTL as a cache
    """
    cached = cache.get(key)
    if cached:
        return json.loads(cached) if as_json else cached

    calculated = calculate()
    cache.set(key, json.dumps(calculated) if as_json else calculated, ttl)

    return calculated


def datetime_to_ms(dt):
    """
    Converts a datetime to a millisecond accuracy timestamp
    """
    seconds = calendar.timegm(dt.utctimetuple())
    return seconds * 1000 + dt.microsecond / 1000


def ms_to_datetime(ms):
    """
    Converts a millisecond accuracy timestamp to a datetime
    """
    dt = datetime.datetime.utcfromtimestamp(ms/1000)
    return dt.replace(microsecond=(ms % 1000) * 1000).replace(tzinfo=pytz.utc)
