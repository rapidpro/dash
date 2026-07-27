from datetime import datetime, timezone as tzone

import phonenumbers

from django import template

register = template.Library()


@register.simple_tag()
def display_time(text_timestamp, org, time_format=None):

    if not time_format:
        time_format = "%b %d, %Y %H:%M"

    parsed_time = datetime.fromisoformat(text_timestamp)
    if parsed_time.tzinfo is None:
        parsed_time = parsed_time.replace(tzinfo=tzone.utc)
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
