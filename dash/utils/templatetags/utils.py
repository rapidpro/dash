from __future__ import unicode_literals

from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def if_url(context, url_name, yes, no):
    """
    Example:
        %li{ class:"{% if_url 'contacts.contact_read' 'active' '' %}" }
    """
    current = context['request'].resolver_match.url_name
    return yes if url_name == current else no
