from __future__ import absolute_import, unicode_literals

import json
import redis

from dash.utils import random_string
from dash.orgs.models import Org
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.test import TestCase


class DashTest(TestCase):
    """
    Base class for dashboard test cases
    """
    @classmethod
    def setUpTestData(cls):
        cls.clear_cache()
        cls.superuser = User.objects.create_superuser(username="root", email="super@user.com", password="root")

    @classmethod
    def clear_cache(cls):
        # we are extra paranoid here and actually hardcode redis to 'localhost' and '10'
        # Redis 10 is our testing redis db
        r = redis.StrictRedis(host='localhost', db=10)
        r.flushdb()

    def create_org(self, name, timezone, subdomain):
        return Org.objects.create(name=name, timezone=timezone, subdomain=subdomain, api_token=random_string(32),
                                  created_by=self.superuser, modified_by=self.superuser)

    def login(self, user):
        result = self.client.login(username=user.username, password=user.username)
        self.assertTrue(result, "Couldn't login as %(user)s / %(user)s" % dict(user=user.username))

    def url_get(self, subdomain, url, params=None):
        return self._url_request(subdomain, 'get', url, params)

    def url_post(self, subdomain, url, data=None):
        return self._url_request(subdomain, 'post', url, data)

    def assertLoginRedirect(self, response, subdomain, next_url):
        self.assertRedirects(response, 'http://%s.localhost/users/login/?next=%s' % (subdomain, next_url))

    def _url_request(self, subdomain, method, url, data):
        if data is None:
            data = {}
        extra = {}
        if subdomain:
            extra['HTTP_HOST'] = '%s.localhost' % subdomain
        func = getattr(self.client, method)
        response = func(url, data, **extra)
        if isinstance(response, JsonResponse):
            response.json = json.loads(response.content)
        return response
