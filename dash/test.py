import itertools
import json

import redis
import requests
from requests.structures import CaseInsensitiveDict

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.test import TestCase

from dash.orgs.models import Org
from dash.utils import random_string


class MockResponse:
    """
    Mock response object with a status code and some content
    """

    def __init__(self, status_code, content=None, headers=None):
        self.status_code = status_code
        self.content = content or ""
        self.headers = CaseInsensitiveDict()

        if headers:
            self.headers.update(headers)

    def raise_for_status(self):
        http_error_msg = ""

        if 400 <= self.status_code < 500:
            http_error_msg = "%s Client Error: ..." % self.status_code

        elif 500 <= self.status_code < 600:
            http_error_msg = "%s Server Error: ..." % self.status_code

        if http_error_msg:
            raise requests.HTTPError(http_error_msg, response=self)

    def json(self, **kwargs):
        return json.loads(self.content)


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
        r = redis.StrictRedis(host="localhost", db=10)
        r.flushdb()

    def create_org(self, name, timezone, subdomain):
        org = Org.objects.create(
            name=name, timezone=timezone, subdomain=subdomain, created_by=self.superuser, modified_by=self.superuser
        )
        org.backends.get_or_create(
            api_token=random_string(32), slug="rapidpro", created_by=self.superuser, modified_by=self.superuser
        )
        return org

    def login(self, user):
        password = "root" if user == self.superuser else user.username
        result = self.client.login(username=user.username, password=password)
        self.assertTrue(result, "Couldn't login as %(user)s / %(user)s" % dict(user=user.username))

    def url_get(self, subdomain, url, params=None, **extra):
        return self._url_request(subdomain, "get", url, params, **extra)

    def url_post(self, subdomain, url, data=None, **extra):
        return self._url_request(subdomain, "post", url, data, **extra)

    def assertLoginRedirect(self, response, subdomain, next_url):
        self.assertRedirects(response, "http://%s.localhost/users/login/?next=%s" % (subdomain, next_url))

    def _url_request(self, subdomain, method, url, data, **extra):
        if data is None:
            data = {}

        if subdomain:
            extra["HTTP_HOST"] = "%s.localhost" % subdomain

        func = getattr(self.client, method)
        response = func(url, data, **extra)

        if isinstance(response, JsonResponse):
            content = response.content
            if isinstance(content, bytes):
                content = content.decode("utf-8")

            response.json = json.loads(content)

        return response


class MockClientQuery:
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
        return "cursor-string"

    def __iter__(self):
        return self

    def __next__(self):
        if not self.fetches:
            raise StopIteration()

        return self.fetches.pop(0)
