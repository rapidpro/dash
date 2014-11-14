import traceback
from django.conf import settings
from django.template.response import TemplateResponse
from django.utils import translation
from django.core.exceptions import DisallowedHost
from dash.orgs.models import Org


class SetOrgMiddleware(object):


    def process_request(self, request):
        user = request.user

        host = 'localhost'
        try:
            host = request.get_host()
        except DisallowedHost:
            traceback.print_exc()

        subdomain = None

        parts = host.split('.')

        # at this point we might be something like 'uganda.localhost'
        if parts > 1:
            subdomain = parts[0]
            parts = parts[1:]

            # we keep stripping subdomains if the subdomain is something
            # like 'www' and there are more parts
            while len(parts) > 2 and subdomain == 'www':
                subdomain = parts[0]
                parts = parts[1:]

        org = None
        if subdomain:
            orgs = Org.objects.filter(subdomain__iexact=subdomain)
            if orgs:
                org = orgs[0]

        # no org and not org choosing page? display our chooser page
        if not org and request.path.find('/manage/org') != 0 and request.path.find('/users/') != 0 and request.path.find(settings.STATIC_URL) != 0:
            orgs = Org.objects.filter(is_active=True)

            if not user.is_anonymous():
                user.set_org(org)

            request.org = org

            # populate a 'host' attribute on each org so we can link off to them
            for org in orgs:
                org.host = settings.SITE_HOST_PATTERN % org.subdomain

            return TemplateResponse(request, settings.SITE_CHOOSER_TEMPLATE, dict(orgs=orgs))

        else:
            if not user.is_anonymous():
                user.set_org(org)

            # activate the default language for this org
            language = settings.DEFAULT_LANGUAGE
            if org and org.language:
                language = org.language

            translation.activate(language)

            request.org = org

