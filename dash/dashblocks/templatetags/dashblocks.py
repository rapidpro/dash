from django import template
from django.conf import settings
from django.db.models import Prefetch

from dash.dashblocks.models import DashBlock, DashBlockType

"""
This module offers one templatetag called ``load_dashblocks``.

``load_dashblocks`` does a query for all active DashBlock objects
for the passed in DashBlockType and Org on request. (identified by the slug)
You can then access that list within your context.

It accepts 2 parameter:

    org
        The Org set on the request to filter DashBlocks for that org.

    slug
        The slug/key of the DashBlockType to load DashBlocks for.

        If you want to pass it by name, you have to use quotes on it.
        Otherwise just use the variable name.

Syntax::

    {% load_dashblocks [org] [name] %}

Example usage::

    {% load dashblocks %}

    ...

    {% load_dashblocks request.org "home_banner_blocks" %}

    ...

    Note: You may also use the shortcut tag 'load_qbs'
    eg: {% load_qbs request.org "home_banner_blocks %}

.. note::

    If you specify a slug that has no associated dash block, then an error message
    will be inserted in your template.  You may change this text by setting
    the value of the DASHBLOCK_STRING_IF_INVALID setting.

"""


register = template.Library()


@register.simple_tag(takes_context=True)
def load_dashblocks(context, org, slug, tag=None):
    if not org:
        return ""

    dashblocks_qs = DashBlock.objects.filter(org=org, is_active=True).order_by("-priority")
    # filter by our tag if one was specified
    if tag is not None:
        dashblocks_qs = dashblocks_qs.filter(tags__icontains=tag)

    dashblock_type = (
        DashBlockType.objects.filter(slug=slug)
        .prefetch_related(
            Prefetch(
                "dashblock_set",
                queryset=dashblocks_qs,
                to_attr="prefetch_dashblocks",
            )
        )
        .first()
    )

    if not dashblock_type:
        default_invalid = '<b><font color="red">DashBlockType with slug: %s not found</font></b>'
        return getattr(settings, "DASHBLOCK_STRING_IF_INVALID", default_invalid) % slug

    dashblocks = dashblock_type.prefetch_dashblocks

    context[slug] = dashblocks

    return ""


@register.simple_tag(takes_context=True)
def load_qbs(context, org, slug, tag=None):
    return load_dashblocks(context, org, slug, tag)
