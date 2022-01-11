from datetime import datetime

import phonenumbers

from django import template
from django.utils import timezone

register = template.Library()


@register.simple_tag()
def display_time(text_timestamp, org, time_format=None):

    if not time_format:
        time_format = "%b %d, %Y %H:%M"

    parsed_time = datetime.strptime(text_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    output_time = parsed_time.astimezone(org.timezone)

    return output_time.strftime(time_format)


@register.simple_tag()
def national_phone(number_str):
    if number_str and number_str[0] == "+":
        try:
            return phonenumbers.format_number(
                phonenumbers.parse(number_str, None), phonenumbers.PhoneNumberFormat.NATIONAL
            )
        except Exception:
            # number didn't parse, return it raw
            return number_str

    return number_str
