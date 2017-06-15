from __future__ import unicode_literals

import json
import itertools
import redis
import six

from dash.orgs.models import Org
from dash.utils import random_string
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.test import TestCase


class DashTest(TestCase):
    """
    Base class for dashboard test cases
    """
    def setUp(self):
        super(DashTest, self).setUp()

        self.superuser = User.objects.create_superuser(username="testroot", email="super@user.com", password="root")

        self.clear_cache()

    @classmethod
    def clear_cache(cls):
        # we are extra paranoid here and actually hardcode redis to 'localhost' and '10'
        # Redis 10 is our testing redis db
        r = redis.StrictRedis(host='localhost', db=10)
        r.flushdb()

    def create_org(self, name, timezone, subdomain):
        return Org.objects.create(
            name=name, timezone=timezone, subdomain=subdomain, api_token=random_string(32),
            created_by=self.superuser, modified_by=self.superuser)

    def login(self, user):
        result = self.client.login(username=user.username, password=user.username)
        self.assertTrue(result, "Couldn't login as %(user)s / %(user)s" % dict(user=user.username))

    def url_get(self, subdomain, url, params=None, **extra):
        return self._url_request(subdomain, 'get', url, params, **extra)

    def url_post(self, subdomain, url, data=None, **extra):
        return self._url_request(subdomain, 'post', url, data, **extra)

    def assertLoginRedirect(self, response, subdomain, next_url):
        self.assertRedirects(response,
                             'http://%s.localhost/users/login/?next=%s' % (subdomain, next_url))

    def _url_request(self, subdomain, method, url, data, **extra):
        if data is None:
            data = {}

        if subdomain:
            extra['HTTP_HOST'] = '%s.localhost' % subdomain

        func = getattr(self.client, method)
        response = func(url, data, **extra)

        if isinstance(response, JsonResponse):
            content = response.content
            if isinstance(content, six.binary_type):
                content = content.decode('utf-8')

            response.json = json.loads(content)

        return response


class MockClientQuery(six.Iterator):
    """
    Mock for APIv2 client get_xxxxx return values. Pass lists of temba objects to mock each fetch the client would make.

    For example:
        mock_get_contacts.return_value = MockClientQuery(
            [TembaContact.create(...), TembaContact.create(...), TembaContact.create(...)]
            [TembaContact.create(...)]
        )

    Will return the three contacts on the first call to iterfetches, and one on the second call.

    """
    def __init__(self, *fetches):
        self.fetches = list(fetches)

    def iterfetches(self, *args, **kwargs):
        return self

    def all(self, *args, **kwargs):
        return list(itertools.chain.from_iterable(self.fetches))

    def first(self, *args, **kwargs):
        return self.fetches[0][0] if self.fetches[0] else None

    def get_cursor(self):
        return 'cursor-string'

    def __iter__(self):
        return self

    def __next__(self):
        if not self.fetches:
            raise StopIteration()

        return self.fetches.pop(0)
