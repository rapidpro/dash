import traceback
from django.conf import settings
from django.template.response import TemplateResponse
from django.utils import translation, timezone
from django.core.exceptions import DisallowedHost
from dash.orgs.models import Org


class SetOrgMiddleware(object):
    """
    Sets the org on the request, based on the subdomain
    """
    def process_request(self, request):
        subdomain = self.get_subdomain(request)

        if subdomain:
            request.org = Org.objects.filter(subdomain__iexact=subdomain).first()
        else:
            request.org = None

        if not request.user.is_anonymous():
            request.user.set_org(request.org)

        if not request.org:
            # only some pages can be viewed without an org
            patterns = getattr(settings, 'SITE_ALLOW_NO_ORG', ('/manage/org', '/users/', settings.STATIC_URL))
            allow_for_path = False
            for pattern in patterns:
                if request.path.startswith(pattern):
                    allow_for_path = True
                    break

            if not allow_for_path:
                all_orgs = Org.objects.filter(is_active=True)

                # populate a 'host' attribute on each org so we can link off to them
                for org in all_orgs:
                    org.host = settings.SITE_HOST_PATTERN % org.subdomain

                return TemplateResponse(request, settings.SITE_CHOOSER_TEMPLATE, dict(orgs=all_orgs))

        else:
            # activate the default language for this org
            language = settings.DEFAULT_LANGUAGE
            if request.org.language:
                language = request.org.language

            translation.activate(language)

            # activate timezone for this org
            if request.org.timezone:
                timezone.activate(request.org.timezone)

    @staticmethod
    def get_subdomain(request):
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

        return subdomain


