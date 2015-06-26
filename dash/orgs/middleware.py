from __future__ import absolute_import, unicode_literals
import re
import traceback

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils import translation, timezone

from dash.orgs.models import Org


ALLOW_NO_ORG = (
    'users.user_login',
    'users.user_logout',
    'users.user_create',
    'users.user_list',
    'users.user_update',
    'users.user_profile',
    'users.user_forget',
    'users.user_recover',
    'users.user_expired',
    'users.user_failed',
    'users.user_newpassword',
    'users.user_mimic',
    'orgs.org_create',
    'orgs.org_list',
    'orgs.org_update',
    'orgs.org_choose',
    'orgs.org_home',
    'orgs.org_edit',
    'orgs.org_manage_accounts',
    'orgs.org_create_login',
    'orgs.org_join',
    'orgs.orgbackground_create',
    'orgs.orgbackground_update',
    'orgs.orgbackground_list'
)


class SetOrgMiddleware(object):
    """
    Sets the org on the request, based on the subdomain
    """
    def process_request(self, request):
        subdomain = self.get_subdomain(request)

        org = Org.objects.filter(subdomain__iexact=subdomain, is_active=True).first()

        if not request.user.is_anonymous():
            request.user.set_org(org)

        if org:
            request.org = org

            # activate the default language for this org
            language = settings.DEFAULT_LANGUAGE
            if org.language:
                language = org.language

            translation.activate(language)

            # activate timezone for this org
            if org.timezone:
                timezone.activate(org.timezone)
        else:
            request.org = None

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.org:
            # serve static files
            media_url = getattr(settings, 'MEDIA_URL', None)
            static_url = getattr(settings, 'STATIC_URL', None)
            path = request.path

            if (media_url and path.startswith(media_url)) or (static_url and path.startswith(static_url)):
                return None

            # only some pages can be viewed without an org
            url_name = request.resolver_match.url_name
            whitelist = ALLOW_NO_ORG + getattr(settings, 'SITE_ALLOW_NO_ORG', ())

            # make sure the chooser view is whitelisted
            chooser_view = getattr(settings, 'SITE_CHOOSER_URL_NAME', 'orgs.org_chooser')
            whitelist += (chooser_view,)

            if url_name not in whitelist:
                return HttpResponseRedirect(reverse(chooser_view))

    @staticmethod
    def get_subdomain(request):
        host = 'localhost'
        try:
            host = request.get_host()
        except DisallowedHost:
            traceback.print_exc()

        subdomain = ""

        # does the host look like an IP? return ""
        if re.match("^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", host):
            return subdomain

        parts = host.split('.')

        # for more than 2 parts
        if len(parts) > 2:
            subdomain = parts[0]
            parts = parts[1:]

            # we keep stripping subdomains if the subdomain is something
            # like 'www' and there are more parts
            while subdomain.lower() == 'www' and len(parts) > 1:
                subdomain = parts[0]
                parts = parts[1:]

        elif len(parts) > 0:
            # for less than or equal to 2 parts
            # subdomain is the first word in the parts
            subdomain = parts[0]
            hostname = getattr(settings, 'HOSTNAME', '')
            domain_first_part = hostname.lower().split('.')[0]

            # if the subdomain is the same as the first part of hostname
            # ignore than and return ''
            if subdomain.lower() in [domain_first_part, 'localhost']:
                subdomain = ""

        return subdomain
