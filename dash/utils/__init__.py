from __future__ import absolute_import, unicode_literals

import calendar
import datetime
import json
from django.conf import settings
import pytz
import random

from django.core.cache import cache
from django.utils import timezone
from dateutil.relativedelta import relativedelta




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


def get_cacheable(cache_key, cache_ttl, calculate):
    """
    Gets the result of a method call, using the given key and TTL as a cache
    """
    cached = cache.get(cache_key)
    if cached is not None:
        return json.loads(cached)

    calculated = calculate()
    cache.set(cache_key, json.dumps(calculated), cache_ttl)

    return calculated


def get_obj_cacheable(obj, attr_name, calculate):
    """
    Gets the result of a method call, using the given object and attribute name as a cache
    """
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name)

    calculated = calculate()
    setattr(obj, attr_name, calculated)

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


def get_month_range(d=None):
    """
    Gets the start (inclusive) and end (exclusive) datetimes of the current month in the same timezone as the given date
    """
    if not d:
        d = timezone.now()

    start = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start + relativedelta(months=1)
    return start, end


def chunks(data, size):
    """
    Yield successive chunks from the given slice-able collection
    """
    for i in xrange(0, len(data), size):
        yield data[i:(i + size)]


def temba_client_flow_results_serializer(client_results):
    if not client_results:
        return client_results

    json_results = []
    for flow_result in client_results:
        flow_result_json = dict()
        flow_result_json['set'] = flow_result.set
        flow_result_json['unset'] = flow_result.unset
        flow_result_json['open_ended'] = flow_result.open_ended
        flow_result_json['label'] = flow_result.label
        flow_result_json['categories'] = [ dict(label=category.label, count=category.count) for category in flow_result.categories]
        if flow_result.boundary:
            flow_result_json['boundary'] = flow_result.boundary

        json_results.append(flow_result_json)

    return json_results
