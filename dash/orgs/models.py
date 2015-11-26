from __future__ import absolute_import, unicode_literals
from datetime import datetime
import json
import random

import pytz
from smartmin.models import SmartModel
from temba_client.client import TembaClient

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text, python_2_unicode_compatible

from dash.dash_email import send_dash_email
from dash.utils import datetime_to_ms


STATE = 1
DISTRICT = 2

# we cache boundary data for a month at a time
BOUNDARY_CACHE_TIME = getattr(settings, 'API_BOUNDARY_CACHE_TIME', 60 * 60 * 24 * 30)

BOUNDARY_CACHE_KEY = 'org:%d:boundaries'
BOUNDARY_LEVEL_1_KEY = 'geojson:%d'
BOUNDARY_LEVEL_2_KEY = 'geojson:%d:%s'


@python_2_unicode_compatible
class Org(SmartModel):
    name = models.CharField(
        verbose_name=_("Name"), max_length=128,
        help_text=_("The name of this organization"))

    logo = models.ImageField(
        upload_to='logos', null=True, blank=True,
        help_text=_("The logo that should be used for this organization"))

    administrators = models.ManyToManyField(
        User, verbose_name=_("Administrators"), related_name="org_admins",
        help_text=_("The administrators in your organization"))

    viewers = models.ManyToManyField(
        User, verbose_name=_("Viewers"), related_name="org_viewers",
        help_text=_("The viewers in your organization"))

    editors = models.ManyToManyField(
        User, verbose_name=_("Editors"), related_name="org_editors",
        help_text=_("The editors in your organization"))

    language = models.CharField(
        verbose_name=_("Language"), max_length=64, null=True, blank=True,
        help_text=_("The main language used by this organization"))

    subdomain = models.SlugField(
        verbose_name=_("Subdomain"), null=True, blank=True, max_length=255, unique=True,
        error_messages=dict(unique=_("This subdomain is not available")),
        help_text=_("The subdomain for this organization"))

    domain = models.CharField(
        verbose_name=_("Domain"), null=True, blank=True, max_length=255, unique=True,
        error_messages=dict(unique=_("This domain is not available")),
        help_text=_("The custom domain for this organization"))

    timezone = models.CharField(
        verbose_name=_("Timezone"), max_length=64, default='UTC',
        help_text=_("The timezone your organization is in."))

    api_token = models.CharField(
        max_length=128, null=True, blank=True,
        help_text=_("The API token for the RapidPro account this dashboard "
                    "is tied to"))

    config = models.TextField(
        null=True, blank=True,
        help_text=_("JSON blob used to store configuration information "
                    "associated with this organization"))

    def set_timezone(self, timezone):
        self.timezone = timezone
        self._tzinfo = None

    def get_timezone(self):
        tzinfo = getattr(self, '_tzinfo', None)

        if not tzinfo:
            # we need to build the pytz timezone object with a context of now
            tzinfo = timezone.now().astimezone(pytz.timezone(self.timezone)).tzinfo
            self._tzinfo = tzinfo

        return tzinfo

    def get_config(self, name, default=None):
        config = getattr(self, '_config', None)

        if config is None:
            if not self.config:
                return default

            config = json.loads(self.config)
            self._config = config

        return config.get(name, default)

    def set_config(self, name, value, commit=True):
        if not self.config:
            config = dict()
        else:
            config = json.loads(self.config)

        config[name] = value
        self.config = json.dumps(config)
        self._config = config

        if commit:
            self.save()

    def get_org_admins(self):
        return self.administrators.all()

    def get_org_editors(self):
        return self.editors.all()

    def get_org_viewers(self):
        return self.viewers.all()

    def get_org_users(self):
        org_users = self.get_org_admins() | self.get_org_editors() | self.get_org_viewers()
        return org_users.distinct()

    def get_user_org_group(self, user):
        if user in self.get_org_admins():
            user._org_group = Group.objects.get(name="Administrators")
        elif user in self.get_org_editors():
            user._org_group = Group.objects.get(name="Editors")
        elif user in self.get_org_viewers():
            user._org_group = Group.objects.get(name="Viewers")
        else:
            user._org_group = None

        return getattr(user, '_org_group', None)

    def get_user(self):
        user = self.administrators.filter(is_active=True).first()
        if user:
            org_user = user
            org_user.set_org(self)
            return org_user

    def get_temba_client(self):
        host = getattr(settings, 'SITE_API_HOST', None)
        agent = getattr(settings, 'SITE_API_USER_AGENT', None)

        if not host:
            host = '%s/api/v1' % settings.API_ENDPOINT  # UReport sites use this

        return TembaClient(host, self.api_token, user_agent=agent)

    def build_host_link(self, user_authenticated=False):
        host_tld = getattr(settings, "HOSTNAME", 'locahost')
        is_secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)

        prefix = 'http://'

        if self.domain and is_secure and not user_authenticated:
            return prefix + str(self.domain)

        if is_secure:
            prefix = 'https://'

        if self.subdomain == '':
            return prefix + host_tld
        return prefix + force_text(self.subdomain) + "." + host_tld

    @classmethod
    def rebuild_org_boundaries_task(cls, org):
        from dash.orgs.tasks import rebuild_org_boundaries
        rebuild_org_boundaries.delay(org.pk)

    def build_boundaries(self):

        this_time = datetime.now()
        temba_client = self.get_temba_client()
        client_boundaries = temba_client.get_boundaries()

        # we now build our cached versions of level 1 (all states) and level 2
        # (all districts for each state) geojson
        states = []
        districts_by_state = dict()
        for boundary in client_boundaries:
            if boundary.level == STATE:
                states.append(boundary)
            elif boundary.level == DISTRICT:
                osm_id = boundary.parent
                if osm_id not in districts_by_state:
                    districts_by_state[osm_id] = []

                districts = districts_by_state[osm_id]
                districts.append(boundary)

        # mini function to convert a list of boundary objects to geojson
        def to_geojson(boundary_list):
            features = [dict(type='Feature',
                             geometry=dict(type=b.geometry.type,
                                           coordinates=b.geometry.coordinates),
                             properties=dict(name=b.name, id=b.boundary, level=b.level))
                        for b in boundary_list]
            return dict(type='FeatureCollection', features=features)

        boundaries = dict()
        boundaries[BOUNDARY_LEVEL_1_KEY % self.id] = to_geojson(states)

        for state_id in districts_by_state.keys():
            boundaries[BOUNDARY_LEVEL_2_KEY % (self.id, state_id)] = to_geojson(
                districts_by_state[state_id])

        key = BOUNDARY_CACHE_KEY % self.pk
        value = {'time': datetime_to_ms(this_time), 'results': boundaries}
        cache.set(key, value, BOUNDARY_CACHE_TIME)

        return boundaries

    def get_boundaries(self):
        key = BOUNDARY_CACHE_KEY % self.pk
        cached_value = cache.get(key, None)
        if cached_value:
            return cached_value['results']
        Org.rebuild_org_boundaries_task(self)

    def get_country_geojson(self):
        boundaries = self.get_boundaries()
        if boundaries:
            key = BOUNDARY_LEVEL_1_KEY % self.id
            return boundaries.get(key, None)

    def get_state_geojson(self, state_id):
        boundaries = self.get_boundaries()
        if boundaries:
            key = BOUNDARY_LEVEL_2_KEY % (self.id, state_id)
            return boundaries.get(key, None)

    def get_top_level_geojson_ids(self):
        org_country_boundaries = self.get_country_geojson()
        return [elt['properties']['id'] for elt in org_country_boundaries['features']]

    @classmethod
    def create_user(cls, email, password):
        user = User.objects.create_user(username=email, email=email, password=password)
        return user

    @classmethod
    def get_org(cls, user):
        if not user:
            return None

        if not hasattr(user, '_org'):
            org = Org.objects.filter(administrators=user, is_active=True).first()
            if org:
                user._org = org

        return getattr(user, '_org', None)

    def __str__(self):
        return self.name


def get_org(obj):
    return getattr(obj, '_org', None)

User.get_org = get_org


def set_org(obj, org):
    obj._org = org

User.set_org = set_org


def get_user_orgs(user):
    if user.is_superuser:
        return Org.objects.all()
    user_orgs = user.org_admins.all() | user.org_editors.all() | user.org_viewers.all()
    return user_orgs.distinct()

User.get_user_orgs = get_user_orgs


def get_org_group(obj):
    org_group = None
    org = obj.get_org()
    if org:
        org_group = org.get_user_org_group(obj)
    return org_group

User.get_org_group = get_org_group


USER_GROUPS = (('A', _("Administrator")),
               ('E', _("Editor")),
               ('V', _("Viewer")))


class Invitation(SmartModel):
    org = models.ForeignKey(
        Org, verbose_name=_("Org"), related_name="invitations",
        help_text=_("The organization to which the account is invited to view"))

    email = models.EmailField(
        verbose_name=_("Email"),
        help_text=_("The email to which we send the invitation of the viewer"))

    secret = models.CharField(
        verbose_name=_("Secret"), max_length=64, unique=True,
        help_text=_("a unique code associated with this invitation"))

    user_group = models.CharField(
        max_length=1, choices=USER_GROUPS, default='V', verbose_name=_("User Role"))

    def save(self, *args, **kwargs):
        if not self.secret:
            secret = Invitation.generate_random_string(64)

            while Invitation.objects.filter(secret=secret):
                secret = Invitation.generate_random_string(64)

            self.secret = secret

        return super(Invitation, self).save(*args, **kwargs)

    @classmethod
    def generate_random_string(cls, length):
        """
        Generatesa a [length] characters alpha numeric secret
        """
        # avoid things that could be mistaken ex: 'I' and '1'
        letters = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        return ''.join([random.choice(letters) for _ in range(length)])

    def send_invitation(self):
        from .tasks import send_invitation_email_task
        send_invitation_email_task(self.id)

    def send_email(self):
        # no=op if we do not know the email
        if not self.email:
            return

        subject = _("%s Invitation") % self.org.name
        template = "orgs/email/invitation_email"
        to_email = self.email

        context = dict(org=self.org, now=timezone.now(), invitation=self)
        context['subject'] = subject
        context['host'] = self.org.build_host_link()

        send_dash_email(to_email, subject, template, context)


BACKGROUND_TYPES = (('B', _("Banner")),
                    ('P', _("Pattern")))


class OrgBackground(SmartModel):
    org = models.ForeignKey(
        Org, verbose_name=_("Org"), related_name="backgrounds",
        help_text=_("The organization in which the image will be used"))

    name = models.CharField(
        verbose_name=_("Name"), max_length=128,
        help_text=_("The name to describe this background"))

    background_type = models.CharField(
        max_length=1, choices=BACKGROUND_TYPES, default='P', verbose_name=_("Background type"))

    image = models.ImageField(upload_to='org_bgs', help_text=_("The image file"))
