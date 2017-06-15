from __future__ import unicode_literals

import re
import traceback

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils import translation, timezone
from django.utils.deprecation import MiddlewareMixin
from .models import Org


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


class SetOrgMiddleware(MiddlewareMixin):
    """
    Sets the org on the request, based on the subdomain
    """
    def process_request(self, request):

        # try looking the domain level
        host_parts = self.get_host_parts(request)

        org = None
        # the domain is something like 'ureport.bi' or 'ureport.co.ug'
        if len(host_parts) >= 2:
            # we might have a three part domain like 'ureport.co.ug'
            domain = ".".join(host_parts[-3:])
            org = Org.objects.filter(domain__iexact=domain, is_active=True).first()

            if not org:
                # try now the two last part for domains like 'ureport.bi'
                domain = ".".join(host_parts[-2:])
                org = Org.objects.filter(domain__iexact=domain, is_active=True).first()

        elif host_parts:
            # we have a domain like 'localhost'
            domain = host_parts[0]
            org = Org.objects.filter(domain__iexact=domain, is_active=True).first()

        # no custom domain found, try the subdomain
        if not org:
            subdomain = self.get_subdomain(request)

            org = Org.objects.filter(subdomain__iexact=subdomain, is_active=True).first()

        if not request.user.is_anonymous():
            request.user.set_org(org)

        request.org = org

        self.set_language(request, org)
        self.set_timezone(request, org)

    def set_language(self, request, org):
        """Set the current language from the org configuration."""
        if org:
            lang = org.language or settings.DEFAULT_LANGUAGE
            translation.activate(lang)

    def set_timezone(self, request, org):
        """Set the current timezone from the org configuration."""
        if org and org.timezone:
            timezone.activate(org.timezone)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.org:
            # serve static files
            media_url = getattr(settings, 'MEDIA_URL', None)
            static_url = getattr(settings, 'STATIC_URL', None)
            path = request.path

            if media_url and path.startswith(media_url):
                return None
            if static_url and path.startswith(static_url):
                return None

            # only some pages can be viewed without an org
            url_name = request.resolver_match.url_name
            whitelist = ALLOW_NO_ORG + getattr(settings, 'SITE_ALLOW_NO_ORG', ())

            # make sure the chooser view is whitelisted
            chooser_view = getattr(settings, 'SITE_CHOOSER_URL_NAME', 'orgs.org_chooser')
            whitelist += (chooser_view,)

            if url_name not in whitelist:
                return HttpResponseRedirect(reverse(chooser_view))

    def get_host_parts(self, request):
        host = 'localhost'
        try:
            host = request.get_host()
        except DisallowedHost:
            traceback.print_exc()

        # does the host look like an IP? return []
        if re.match("^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", host):
            return []

        return host.split('.')

    def get_subdomain(self, request):

        subdomain = ""
        parts = self.get_host_parts(request)
        host_string = ".".join(parts)

        # we only look up subdomains for localhost and the configured hostname only
        top_domains = ['localhost:8000', 'localhost', getattr(settings, 'HOSTNAME', "")]
        allowed_top_domain = False
        for top in top_domains:
            if host_string.endswith(top):
                allowed_top_domain = True
                break

        # if empty parts or domain neither localhost nor hostname return ""
        if not parts or not allowed_top_domain:
            return subdomain

        # if we have parts for domain like 'www.nigeria.ureport.in'
        if len(parts) > 2:
            subdomain = parts[0]
            parts = parts[1:]

            # we keep stripping subdomains if the subdomain is something
            # like 'www' and there are more parts
            while subdomain.lower() == 'www' and len(parts) > 1:
                subdomain = parts[0]
                parts = parts[1:]

        elif len(parts) > 0:
            # for domains like 'ureport.in' we just take the first part
            subdomain = parts[0]

        # get the configured hostname
        hostname = getattr(settings, 'HOSTNAME', '')
        domain_first_part = hostname.lower().split('.')[0]

        # if the subdomain is the same as the first part of hostname
        # ignore than and return ''
        if subdomain.lower() in [domain_first_part, 'localhost']:
            subdomain = ""

        return subdomain
