from __future__ import absolute_import, unicode_literals

import datetime
import pytz

ISO8601_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def format_iso8601(_datetime):
    """
    Formats a datetime as a UTC ISO8601 date
    """
    return _datetime.astimezone(pytz.UTC).strftime(ISO8601_FORMAT)


def parse_iso8601(text):
    """
    Parses a datetime as a UTC ISO8601 date
    """
    return datetime.datetime.strptime(text, ISO8601_FORMAT).replace(tzinfo=pytz.UTC)


def intersection(*args):
    """
    Return the intersection of lists
    """
    if not args:
        return []

    result = set(args[0])
    for l in args[1:]:
        result &= set(l)

    return list(result)


def union(*args):
    """
    Return the union of lists
    """
    if not args:
        return []

    result = set(args[0])
    for l in args[1:]:
        result |= set(l)

    return list(result)