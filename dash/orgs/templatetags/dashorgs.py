from __future__ import unicode_literals

import phonenumbers
import pytz

from datetime import datetime
from django import template


register = template.Library()


@register.simple_tag()
def display_time(text_timestamp, org, time_format=None):

    if not time_format:
        time_format = '%b %d, %Y %H:%M'

    utc_tz = pytz.timezone('UTC')
    parsed_time = utc_tz.localize(datetime.strptime(text_timestamp, '%Y-%m-%dT%H:%M:%SZ'))
    output_time = parsed_time.astimezone(org.timezone)

    return output_time.strftime(time_format)


@register.simple_tag()
def national_phone(number_str):
    if number_str and number_str[0] == '+':
        try:
            return phonenumbers.format_number(phonenumbers.parse(number_str, None),
                                              phonenumbers.PhoneNumberFormat.NATIONAL)
        except:
            # number didn't parse, return it raw
            return number_str

    return number_str
