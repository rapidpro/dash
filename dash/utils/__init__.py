from __future__ import division, unicode_literals

import calendar
import datetime
import json
import pytz
import random
import six

from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.utils import timezone


def intersection(*args):
    """
    Return the intersection of lists, using the first list to determine item order
    """
    if not args:
        return []

    # remove duplicates from first list whilst preserving order
    base = list(OrderedDict.fromkeys(args[0]))

    if len(args) == 1:
        return base
    else:
        others = set(args[1]).intersection(*args[2:])
        return [e for e in base if e in others]


def union(*args):
    """
    Return the union of lists, ordering by first seen in any list
    """
    if not args:
        return []

    base = args[0]
    for other in args[1:]:
        base.extend(other)

    return list(OrderedDict.fromkeys(base))  # remove duplicates whilst preserving order


def random_string(length):
    """
    Generates a random alphanumeric string
    """
    # avoid things that could be mistaken ex: 'I' and '1'
    letters = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return ''.join([random.choice(letters) for _ in range(length)])


def filter_dict(d, keys):
    """
    Creates a new dict from an existing dict that only has the given keys
    """
    return {k: v for k, v in six.iteritems(d) if k in keys}


def get_cacheable(cache_key, cache_ttl, calculate, recalculate=False):
    """
    Gets the result of a method call, using the given key and TTL as a cache
    """
    if not recalculate:
        cached = cache.get(cache_key)
        if cached is not None:
            return json.loads(cached)

    calculated = calculate()
    cache.set(cache_key, json.dumps(calculated), cache_ttl)

    return calculated


def get_obj_cacheable(obj, attr_name, calculate, recalculate=False):
    """
    Gets the result of a method call, using the given object and attribute name
    as a cache
    """
    if not recalculate and hasattr(obj, attr_name):
        return getattr(obj, attr_name)

    calculated = calculate()
    setattr(obj, attr_name, calculated)

    return calculated


def datetime_to_ms(dt):
    """
    Converts a datetime to a millisecond accuracy timestamp
    """
    seconds = calendar.timegm(dt.utctimetuple())
    return seconds * 1000 + int(dt.microsecond / 1000)


def ms_to_datetime(ms):
    """
    Converts a millisecond accuracy timestamp to a datetime
    """
    dt = datetime.datetime.utcfromtimestamp(ms / 1000)
    return dt.replace(microsecond=(ms % 1000) * 1000).replace(tzinfo=pytz.utc)


def get_month_range(d=None):
    """
    Gets the start (inclusive) and end (exclusive) datetimes of the current
    month in the same timezone as the given date
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
    if not isinstance(data, list):
        data = list(data)

    for i in six.moves.xrange(0, len(data), size):
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
        flow_result_json['categories'] = [dict(label=category.label, count=category.count)
                                          for category in flow_result.categories]
        if flow_result.boundary:
            flow_result_json['boundary'] = flow_result.boundary

        json_results.append(flow_result_json)

    return json_results


def is_dict_equal(d1, d2, keys=None, ignore_none_values=True):
    """
    Compares two dictionaries to see if they are equal
    :param d1: the first dictionary
    :param d2: the second dictionary
    :param keys: the keys to limit the comparison to (optional)
    :param ignore_none_values: whether to ignore none values
    :return: true if the dictionaries are equal, else false
    """
    if keys or ignore_none_values:
        d1 = {k: v for k, v in six.iteritems(d1)
              if (keys is None or k in keys) and (v is not None or not ignore_none_values)}
        d2 = {k: v for k, v in six.iteritems(d2)
              if (keys is None or k in keys) and (v is not None or not ignore_none_values)}

    return d1 == d2
