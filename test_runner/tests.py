import zoneinfo
from dash.tags.models import Tag
from unittest.mock import Mock, patch, call

import redis
from smartmin.tests import SmartminTest
from temba_client.v2 import TembaClient

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.exceptions import DisallowedHost
from django.db.utils import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.urls import ResolverMatch, reverse
from django.utils.encoding import force_str

from dash.categories.fields import CategoryChoiceField
from dash.categories.models import Category, CategoryImage
from dash.dashblocks.models import DashBlock, DashBlockImage, DashBlockType
from dash.dashblocks.templatetags.dashblocks import load_qbs
from dash.orgs.context_processors import GroupPermWrapper
from dash.orgs.middleware import SetOrgMiddleware
from dash.orgs.models import Invitation, Org, OrgBackend, OrgBackground, TaskState
from dash.orgs.tasks import org_task
from dash.orgs.templatetags.dashorgs import display_time, national_phone
from dash.stories.models import Story, StoryImage
from dash.utils import random_string
from dash.test import MockResponse


class UserTest(SmartminTest):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="super", email="super@user.com", password="super")

        self.admin = self.create_user("Administrator")

    def test_user_profile(self):
        profile_url = reverse("users.user_profile", args=[self.admin.pk])

        response = self.client.get(profile_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)

        post_data = dict(
            username="denzel@nyaruka.com",
            first_name="Denzel",
            last_name="Washington",
            email="washington@nyaruka.com",
            old_password="Administrator",
            new_password="Washington2",
            confirm_new_password="Washington2",
        )

        response = self.client.post(profile_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        new_admin = User.objects.get(pk=self.admin.pk)
        self.assertEqual(new_admin.username, "washington@nyaruka.com")
        self.assertEqual(new_admin.email, "washington@nyaruka.com")
        self.assertFalse(User.objects.filter(username="denzel@nyaruka.com"))

    def test_user_create(self):
        create_url = reverse("users.user_create")

        response = self.client.get(create_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)

        response = self.client.get(create_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(create_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        self.assertEqual(len(response.context["form"].fields), 7)

    def test_user_update(self):
        update_url = reverse("users.user_update", args=[self.admin.pk])

        response = self.client.get(update_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)

        response = self.client.get(update_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(update_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        self.assertEqual(len(response.context["form"].fields), 8)


class DashTest(SmartminTest):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="super", email="super@user.com", password="super")

        self.admin = self.create_user("Administrator")

        # Clear DashBlockType from old migrations
        DashBlockType.objects.all().delete()

    def clear_cache(self):
        # hardcoded to localhost
        r = redis.StrictRedis(host="localhost", db=1)
        r.flushdb()

    def clear_uploads(self):
        import os

        for org_bg in OrgBackground.objects.all():
            os.remove(org_bg.image.path)

        for cat_image in CategoryImage.objects.all():
            os.remove(cat_image.image.path)

        for story_image in StoryImage.objects.all():
            os.remove(story_image.image.path)

        for dash_image in DashBlockImage.objects.all():
            os.remove(dash_image.image.path)

    def create_org(self, subdomain, user):

        name = subdomain

        orgs = Org.objects.filter(subdomain=subdomain)
        if orgs:
            org = orgs[0]
            org.name = name
            org.save()
        else:
            org = Org.objects.create(subdomain=subdomain, name=name, language="en", created_by=user, modified_by=user)

        org.administrators.add(user)

        self.assertEqual(Org.objects.filter(subdomain=subdomain).count(), 1)

        org_backend = org.backends.filter(slug="rapidpro").first()

        if not org_backend:
            org.backends.get_or_create(api_token=random_string(32), slug="rapidpro", created_by=user, modified_by=user)
        return Org.objects.get(subdomain=subdomain)

    def read_json(self, filename):
        from django.conf import settings

        handle = open("%s/test_api/%s.json" % (settings.TESTFILES_DIR, filename))
        contents = handle.read()
        handle.close()
        return contents


class SetOrgMiddlewareTest(DashTest):
    def setUp(self):
        super(SetOrgMiddlewareTest, self).setUp()

        self.middleware = SetOrgMiddleware(self.get_response)

    def get_response(request):
        return HttpResponse()

    def mock_view(self, request):
        return MockResponse(204)

    def simulate_process(self, host, url_name, path="/"):
        """
        Simulates the application of org middleware
        """
        self.request = Mock(spec=HttpRequest)
        self.request.get_host.return_value = host
        self.request.user = self.admin
        self.request.path = path
        self.request.META = dict(HTTP_HOST=None)

        response = self.middleware.process_request(self.request)
        if response:
            return response

        self.request.resolver_match = ResolverMatch(self.mock_view, [], {}, url_name)

        return self.middleware.process_view(self.request, self.mock_view, [], {})

    def test_process(self):
        # media url and static url are always whitelisted
        response = self.simulate_process("ureport.io", "", "/media/image.jpg")
        self.assertIsNone(response)
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())

        response = self.simulate_process("ureport.io", "", "/static/css/style.css")
        self.assertIsNone(response)
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())

        # check white-listed URL with no orgs
        response = self.simulate_process("ureport.io", "orgs.org_create")
        self.assertIsNone(response)
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())

        # check non-white-listed URL with no orgs
        response = self.simulate_process("ureport.io", "dash.test_test")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse(settings.SITE_CHOOSER_URL_NAME))
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())

        # create some orgs..
        ug_org = self.create_org("uganda", self.admin)
        rw_org = self.create_org("rwanda", self.admin)

        # now orgs should be listed in choose page
        response = self.simulate_process("ureport.io", "dash.test_test")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse(settings.SITE_CHOOSER_URL_NAME))
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())

        # white-listing this URL name prevents choose response
        with self.settings(SITE_ALLOW_NO_ORG=("dash.test_test",)):
            response = self.simulate_process("ureport.io", "dash.test_test")
            self.assertIsNone(response)
            self.assertIsNone(self.request.org)
            self.assertIsNone(self.request.user.get_org())

        # check requests to valid host names based on the Ug org's subdomain
        for host in ("uganda.ureport.io", "www.UGANDA.ureport.io", "uganda.staging.ureport.io", "uganda.localhost"):

            # check white-listed URL
            response = self.simulate_process(host, "orgs.org_create")
            self.assertIsNone(response)
            self.assertEqual(self.request.org, ug_org)
            self.assertEqual(self.request.user.get_org(), ug_org)

            # check non-white-listed URL
            response = self.simulate_process(host, "dash.test_test")
            self.assertIsNone(response)
            self.assertEqual(self.request.org, ug_org)
            self.assertEqual(self.request.user.get_org(), ug_org)

        # test invalid subdomain
        response = self.simulate_process("blabla.ureport.io", "dash.test_test")
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse(settings.SITE_CHOOSER_URL_NAME))

        # test disallowed host exception
        self.request.get_host.side_effect = DisallowedHost

        response = self.simulate_process("xxx.ureport.io", "dash.test_test")
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse(settings.SITE_CHOOSER_URL_NAME))

        rw_org.is_active = False
        rw_org.save()

        response = self.simulate_process("rwanda.ureport.io", "dash.test_test")
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse(settings.SITE_CHOOSER_URL_NAME))

        with self.settings(SITE_CHOOSER_URL_NAME="dash.test_chooser"):
            response = self.simulate_process("ureport.io", "dash.test_chooser")
            self.assertIsNone(response)
            self.assertIsNone(self.request.org)
            self.assertIsNone(self.request.user.get_org())

        response = self.simulate_process("localhost", "dash.test_test")
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse(settings.SITE_CHOOSER_URL_NAME))

        ug_org.domain = "ureport.co.ug"
        ug_org.save()

        # check white-listed URL
        response = self.simulate_process("ureport.co.ug", "orgs.org_create")
        self.assertIsNone(response)
        self.assertEqual(self.request.org, ug_org)
        self.assertEqual(self.request.user.get_org(), ug_org)

        # check non-white-listed URL
        response = self.simulate_process("ureport.co.ug", "dash.test_test")
        self.assertIsNone(response)
        self.assertEqual(self.request.org, ug_org)
        self.assertEqual(self.request.user.get_org(), ug_org)

        ug_org.domain = "ureport.ug"
        ug_org.save()

        # check white-listed URL
        response = self.simulate_process("ureport.ug", "orgs.org_create")
        self.assertIsNone(response)
        self.assertEqual(self.request.org, ug_org)
        self.assertEqual(self.request.user.get_org(), ug_org)

        # check non-white-listed URL
        response = self.simulate_process("ureport.ug", "dash.test_test")
        self.assertIsNone(response)
        self.assertEqual(self.request.org, ug_org)
        self.assertEqual(self.request.user.get_org(), ug_org)

        # no org with the domain
        response = self.simulate_process("ureport.co.ug", "dash.test_test")
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())
        self.assertEqual(response.status_code, 302)

        # do not check subdomain if not domain has host name
        response = self.simulate_process("uganda.co.ug", "dash.test_test")
        self.assertIsNone(self.request.org)
        self.assertIsNone(self.request.user.get_org())
        self.assertEqual(response.status_code, 302)

        empty_subdomain_org = Org.objects.create(
            subdomain="", name="global", language="en", created_by=self.admin, modified_by=self.admin
        )

        with self.settings(HOSTNAME="ureport.staging.nyaruka.com"):
            response = self.simulate_process("ureport.staging.nyaruka.com", "dash.test_test")
            self.assertIsNone(response)
            self.assertEqual(self.request.org, empty_subdomain_org)
            self.assertEqual(self.request.user.get_org(), empty_subdomain_org)

        response = self.simulate_process("localhost", "dash.test_test")
        self.assertIsNone(response)
        self.assertEqual(self.request.org, empty_subdomain_org)
        self.assertEqual(self.request.user.get_org(), empty_subdomain_org)

        # case get_host gives us an IP
        response = self.simulate_process("1.12.123.123", "dash.test_test")
        self.assertIsNone(response)
        self.assertEqual(self.request.org, empty_subdomain_org)
        self.assertEqual(self.request.user.get_org(), empty_subdomain_org)


class OrgContextProcessorTestcase(DashTest):
    def test_group_perms_wrapper(self):
        administrators = Group.objects.get(name="Administrators")
        editors = Group.objects.get(name="Editors")
        viewers = Group.objects.get(name="Viewers")

        administrators_wrapper = GroupPermWrapper(administrators)
        self.assertTrue(administrators_wrapper["orgs"]["org_edit"])
        self.assertTrue(administrators_wrapper["orgs"]["org_home"])

        editors_wrapper = GroupPermWrapper(editors)
        self.assertFalse(editors_wrapper["orgs"]["org_edit"])
        self.assertTrue(editors_wrapper["orgs"]["org_home"])

        viewers_wrapper = GroupPermWrapper(viewers)
        self.assertFalse(viewers_wrapper["orgs"]["org_edit"])
        self.assertFalse(viewers_wrapper["orgs"]["org_home"])


class OrgBackendTest(DashTest):
    def setUp(self):
        super(OrgBackendTest, self).setUp()

        self.uganda = self.create_org("uganda", self.admin)
        self.nigeria = self.create_org("nigeria", self.admin)

        self.uganda_backend = self.uganda.backends.get(slug="rapidpro")

        self.nigeria_backend = self.nigeria.backends.get(slug="rapidpro")

    def test_list(self):
        list_url = reverse("orgs.orgbackend_list")

        response = self.client.get(list_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(list_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["object_list"])
        self.assertTrue(self.uganda_backend in response.context["object_list"])
        self.assertTrue(self.nigeria_backend in response.context["object_list"])
        self.assertEqual(len(response.context["object_list"]), 2)

        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["object_list"])
        self.assertFalse(self.nigeria_backend in response.context["object_list"])
        self.assertTrue(self.uganda_backend in response.context["object_list"])
        self.assertEqual(len(response.context["object_list"]), 1)

        self.assertEqual(str(self.nigeria_backend), "rapidpro")


class OrgTest(DashTest):
    def setUp(self):
        super(OrgTest, self).setUp()

        self.org = self.create_org("uganda", self.admin)

    def test_org_model(self):
        user = self.create_user("User")

        self.assertEqual(force_str(self.org), "uganda")

        self.assertIsNone(Org.get_org(None))
        self.assertEqual(Org.get_org(self.admin), self.org)
        self.assertIsNone(Org.get_org(user))

        new_user = Org.create_user("email@example.com", "secretpassword")
        self.assertIsInstance(new_user, User)
        self.assertEqual(new_user.email, "email@example.com")
        self.assertEqual(new_user.username, "email@example.com")
        self.assertTrue(new_user.check_password("secretpassword"))

        client = self.org.get_temba_client()
        self.assertIsInstance(client, TembaClient)
        self.assertEqual(client.root_url, "http://localhost:8001/api/v2")
        self.assertEqual(
            client.headers["Authorization"], "Token %s" % self.org.backends.filter(slug="rapidpro").first().api_token
        )
        self.assertRegex(client.headers["User-Agent"], r"rapidpro-python/[\d\.]+")

        client = self.org.get_temba_client(api_version=2)
        self.assertIsInstance(client, TembaClient)
        self.assertEqual(client.root_url, "http://localhost:8001/api/v2")
        self.assertEqual(
            client.headers["Authorization"], "Token %s" % self.org.backends.filter(slug="rapidpro").first().api_token
        )

        org_backend = self.org.backends.filter(slug="rapidpro").first()
        org_backend.host = "http://example.com/"
        org_backend.save()

        client = self.org.get_temba_client(api_version=2)
        self.assertIsInstance(client, TembaClient)
        self.assertEqual(client.root_url, "http://example.com/api/v2")
        self.assertEqual(
            client.headers["Authorization"], "Token %s" % self.org.backends.filter(slug="rapidpro").first().api_token
        )

        self.assertEqual(self.org.get_user(), self.admin)

        viewer = self.create_user("Viewer")
        editor = self.create_user("Editor")
        self.org.viewers.add(viewer)
        self.org.editors.add(editor)

        self.assertTrue(self.org.get_user_org_group(self.admin))
        self.assertEqual(self.org.get_user_org_group(self.admin).name, "Administrators")
        self.assertTrue(self.org.get_user_org_group(editor))
        self.assertEqual(self.org.get_user_org_group(editor).name, "Editors")
        self.assertTrue(self.org.get_user_org_group(viewer))
        self.assertEqual(self.org.get_user_org_group(viewer).name, "Viewers")
        self.assertIsNone(self.org.get_user_org_group(user))

        org_users = self.org.get_org_users()
        self.assertEqual(len(org_users), 3)
        self.assertIn(self.admin, org_users)
        self.assertIn(editor, org_users)
        self.assertIn(viewer, org_users)

        org_admins = self.org.get_org_admins()
        self.assertEqual(len(org_admins), 1)
        self.assertIn(self.admin, org_admins)

        org_editors = self.org.get_org_editors()
        self.assertEqual(len(org_editors), 1)
        self.assertIn(editor, org_editors)

        org_viewers = self.org.get_org_viewers()
        self.assertEqual(len(org_viewers), 1)
        self.assertIn(viewer, org_viewers)

        self.assertIsNone(self.org.get_config("field_name"))
        self.assertEqual(self.org.get_config("field_name", "default"), "default")
        self.org.set_config("field_name", "field_value")
        self.assertEqual(self.org.get_config("field_name"), "field_value")

        self.org.set_config("other_field_name", "other_value")
        self.assertEqual(self.org.get_config("field_name"), "field_value")
        self.assertEqual(self.org.get_config("other_field_name"), "other_value")

        self.org._config = None
        self.assertEqual(self.org.get_config("field_name"), "field_value")
        self.assertEqual(self.org.get_config("other_field_name"), "other_value")

    def test_set_config_commit(self):
        """By default, Org.set_config should commit change to database."""
        self.org.set_config("test", "hello")
        self.assertEqual(self.org.get_config("test"), "hello")
        org = Org.objects.get(pk=self.org.pk)  # refresh from db
        self.assertEqual(org.get_config("test"), "hello")

    def test_set_config_no_commit(self):
        """If commit=False is passed to Org.set_config, changes should not be saved."""
        self.org.set_config("test", "hello", commit=False)
        self.assertEqual(self.org.get_config("test"), "hello")
        org = Org.objects.get(pk=self.org.pk)  # refresh from db
        self.assertIsNone(org.get_config("test"))

    def test_build_host_link(self):
        with self.settings(HOSTNAME="localhost:8000"):
            self.assertEqual(self.org.build_host_link(), "http://uganda.localhost:8000")
            self.assertEqual(self.org.build_host_link(True), "http://uganda.localhost:8000")

            with self.settings(SESSION_COOKIE_SECURE=True):
                self.assertEqual(self.org.build_host_link(), "https://uganda.localhost:8000")
                self.assertEqual(self.org.build_host_link(True), "https://uganda.localhost:8000")

            self.org.subdomain = ""
            self.org.save()

            self.assertEqual(self.org.build_host_link(), "http://localhost:8000")
            self.assertEqual(self.org.build_host_link(True), "http://localhost:8000")

            with self.settings(SESSION_COOKIE_SECURE=True):
                self.assertEqual(self.org.build_host_link(), "https://localhost:8000")
                self.assertEqual(self.org.build_host_link(True), "https://localhost:8000")

            self.org.domain = "ureport.ug"
            self.org.subdomain = "uganda"
            self.org.save()

            self.assertEqual(self.org.build_host_link(), "http://uganda.localhost:8000")
            self.assertEqual(self.org.build_host_link(True), "http://uganda.localhost:8000")

            with self.settings(SESSION_COOKIE_SECURE=True):
                self.assertEqual(self.org.build_host_link(), "http://ureport.ug")
                self.assertEqual(self.org.build_host_link(True), "https://uganda.localhost:8000")

    def test_org_create(self):
        create_url = reverse("orgs.org_create")

        response = self.client.get(create_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(create_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(create_url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(response.context["form"].fields), 8)
        self.assertFalse(Org.objects.filter(name="kLab"))
        self.assertEqual(User.objects.all().count(), 3)

        user_alice = User.objects.create_user("alicefox")

        data = dict(
            name="kLab",
            subdomain="klab",
            domain="ureport.io",
            timezone="Africa/Kigali",
            administrators=[user_alice.pk],
        )

        response = self.client.post(create_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"])
        self.assertTrue(response.context["form"].errors)

        data = dict(
            name="kLab", subdomain="klab", domain="klab.rw", timezone="Africa/Kigali", administrators=[user_alice.pk]
        )
        response = self.client.post(create_url, data, follow=True)
        self.assertNotIn("form", response.context)
        self.assertTrue(Org.objects.filter(name="kLab"))
        org = Org.objects.get(name="kLab")
        self.assertEqual(User.objects.all().count(), 4)
        self.assertTrue(org.administrators.filter(username="alicefox"))
        self.assertEqual(org.timezone, zoneinfo.ZoneInfo("Africa/Kigali"))

        # allow may empty domain orgs
        data = dict(
            name="rwanda", subdomain="rwanda", domain="", timezone="Africa/Kigali", administrators=[user_alice.pk]
        )
        response = self.client.post(create_url, data, follow=True)
        self.assertNotIn("form", response.context)
        self.assertTrue(Org.objects.filter(name="rwanda"))
        self.assertTrue(Org.objects.get(name="rwanda"))

        data = dict(
            name="burundi", subdomain="burundi", domain="", timezone="Africa/Kigali", administrators=[user_alice.pk]
        )
        response = self.client.post(create_url, data, follow=True)
        self.assertNotIn("form", response.context)
        self.assertTrue(Org.objects.filter(name="burundi"))
        self.assertTrue(Org.objects.get(name="burundi"))

    def test_org_update(self):
        update_url = reverse("orgs.org_update", args=[self.org.pk])

        response = self.client.get(update_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(update_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(update_url)
        self.assertEqual(200, response.status_code)
        self.assertFalse(Org.objects.filter(name="Burundi"))
        self.assertEqual(len(response.context["form"].fields), 9)

        post_data = dict(
            name="Burundi",
            timezone="Africa/Bujumbura",
            subdomain="burundi",
            domain="ureport.io",
            is_active=True,
            male_label="male",
            female_label="female",
            administrators=self.admin.pk,
        )

        response = self.client.post(update_url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"])
        self.assertTrue(response.context["form"].errors)

        post_data = dict(
            name="Burundi",
            timezone="Africa/Bujumbura",
            subdomain="burundi",
            domain="ureport.bi",
            is_active=True,
            male_label="male",
            female_label="female",
            administrators=self.admin.pk,
        )
        response = self.client.post(update_url, post_data)
        self.assertEqual(response.status_code, 302)

        response = self.client.post(update_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        org = Org.objects.get(pk=self.org.pk)
        self.assertEqual(org.name, "Burundi")
        self.assertEqual(org.subdomain, "burundi")
        self.assertEqual(org.domain, "ureport.bi")
        self.assertEqual(org.timezone, zoneinfo.ZoneInfo("Africa/Bujumbura"))
        self.assertEqual(response.request["PATH_INFO"], reverse("orgs.org_list"))

    def test_org_list(self):
        list_url = reverse("orgs.org_list")

        response = self.client.get(list_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(list_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["object_list"])
        self.assertTrue(self.org in response.context["object_list"])
        self.assertEqual(len(response.context["fields"]), 4)

    def test_org_choose(self):
        choose_url = reverse("orgs.org_choose")

        OrgBackend.objects.all().delete()
        Org.objects.all().delete()

        response = self.client.get(choose_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(choose_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(choose_url, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse("orgs.org_list"))

        self.login(self.admin)
        response = self.client.get(choose_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(choose_url, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse("users.user_login"))

        self.org = self.create_org("uganda", self.admin)

        # with a subdomain
        response = self.client.get(choose_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 302)
        response = self.client.get(choose_url, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.request["PATH_INFO"], reverse("orgs.org_home"))

        # without subdomain
        response = self.client.get(choose_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("orgs.org_choose"))
        self.assertEqual(len(response.context["orgs"]), 1)
        self.assertTrue(self.org in response.context["orgs"])
        self.assertFalse("org" in response.context)
        self.assertTrue("form" in response.context)
        self.assertEqual(len(response.context["form"].fields), 2)
        self.assertTrue("organization" in response.context["form"].fields)
        self.assertTrue("loc" in response.context["form"].fields)

        org_choices = response.context["form"].fields["organization"].choices.queryset
        self.assertEqual(len(org_choices), 1)
        self.assertTrue(self.org in org_choices)

        post_data = dict(organization=self.org.pk)
        response = self.client.post(choose_url, post_data, follow=True)
        self.assertTrue("org" in response.context)
        self.assertEqual(self.org, response.context["org"])
        self.assertEqual(response.request["PATH_INFO"], reverse("orgs.org_home"))

        user = self.create_user("user")
        other_org = self.create_org("other", user)

        post_data = dict(organization=other_org.pk)
        response = self.client.post(choose_url, post_data, follow=True)
        self.assertFalse("org" in response.context)
        self.assertTrue("form" in response.context)
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(response.request["PATH_INFO"], reverse("orgs.org_choose"))

        self.nigeria = self.create_org("nigeria", self.admin)

        response = self.client.get(choose_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("orgs.org_choose"))
        self.assertEqual(len(response.context["orgs"]), 2)
        self.assertTrue(self.org in response.context["orgs"])
        self.assertTrue(self.nigeria in response.context["orgs"])
        self.assertFalse(other_org in response.context["orgs"])
        self.assertFalse("org" in response.context)
        self.assertTrue("form" in response.context)
        self.assertEqual(len(response.context["form"].fields), 2)
        self.assertTrue("organization" in response.context["form"].fields)
        self.assertTrue("loc" in response.context["form"].fields)

        org_choices = response.context["form"].fields["organization"].choices.queryset
        self.assertEqual(len(org_choices), 2)
        self.assertTrue(self.org in org_choices)
        self.assertTrue(self.nigeria in org_choices)

        post_data = dict(organization=self.nigeria.pk)
        response = self.client.post(choose_url, post_data, follow=True)
        self.assertTrue("org" in response.context)
        self.assertEqual(self.nigeria, response.context["org"])
        self.assertEqual(response.request["PATH_INFO"], reverse("orgs.org_home"))

        # test overriding the user home page
        with self.settings(SITE_USER_HOME="/example/home"):
            response = self.client.post(choose_url, post_data, follow=True)
            self.assertEqual(response.request["PATH_INFO"], "/example/home")

    def test_org_home(self):
        home_url = reverse("orgs.org_home")

        response = self.client.get(home_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(home_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["object"], self.org)
        self.assertEqual(response.context["org"], self.org)

    def test_org_edit(self):

        edit_url = reverse("orgs.org_edit")

        self.login(self.admin)
        self.admin.set_org(self.org)

        org_backend = self.org.backends.get(slug="rapidpro")
        org_backend.api_token = "token"
        org_backend.save()

        response = self.client.get(edit_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"])
        self.assertEqual(len(response.context["form"].fields), 20)
        self.assertEqual(
            len(
                [
                    f
                    for f in response.context["form"].fields.items()
                    if f[1].widget.attrs.get("readonly", "") == "readonly"
                ]
            ),
            9,
        )

        self.assertEqual(response.context["form"].initial["name"], "uganda")
        self.assertEqual(response.context["object"], self.org)
        self.assertEqual(response.context["object"], response.context["org"])
        self.assertEqual(response.context["object"].subdomain, "uganda")

        post_data = dict()
        response = self.client.post(edit_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertTrue(response.context["form"])

        errors = response.context["form"].errors
        self.assertEqual(len(errors.keys()), 2)
        self.assertTrue("name" in errors)
        self.assertTrue("common.shortcode" in errors)
        self.assertEqual(errors["name"][0], "This field is required.")
        self.assertEqual(errors["common.shortcode"][0], "This field is required.")

        post_data = dict(name="Rwanda")
        post_data["common.shortcode"] = "224433"

        response = self.client.post(edit_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 302)

        response = self.client.post(edit_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertFalse("form" in response.context)
        org = Org.objects.get(pk=self.org.pk)
        self.assertEqual(org.name, "Rwanda")
        self.assertEqual(org.get_config("shortcode"), "224433")

        org.set_config("rapidpro.reporter_group", "reporters")

        # can't update read-only
        post_data["rapidpro.reporter_group"] = "members"

        response = self.client.post(edit_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertFalse("form" in response.context)
        org = Org.objects.get(pk=self.org.pk)
        self.assertEqual(org.name, "Rwanda")
        self.assertEqual(org.get_config("shortcode"), "224433")
        self.assertEqual(org.get_config("rapidpro.reporter_group"), "reporters")

        self.assertEqual(response.request["PATH_INFO"], reverse("orgs.org_home"))

        response = self.client.get(edit_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial["common.shortcode"], "224433")
        self.assertEqual(form.initial["name"], "Rwanda")
        self.assertEqual(form.initial["rapidpro.reporter_group"], "reporters")
        self.assertTrue("rapidpro.reporter_group" in response.context["view"].fields)

        # remove rapidpro config then hide its config fields
        org_backend.api_token = ""
        org_backend.save()

        response = self.client.get(edit_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"])
        self.assertEqual(len(response.context["form"].fields), 11)
        self.assertEqual(
            len(
                [
                    f
                    for f in response.context["form"].fields.items()
                    if f[1].widget.attrs.get("readonly", "") == "readonly"
                ]
            ),
            0,
        )

    def test_org_chooser(self):
        chooser_url = reverse("orgs.org_chooser")

        response = self.client.get(chooser_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["orgs"]), 1)
        self.assertTrue(self.org in response.context["orgs"])
        self.assertEqual(response.context["orgs"][0].host, "http://uganda.ureport.io")

        self.org2 = self.create_org("nigeria", self.admin)

        response = self.client.get(chooser_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["orgs"]), 2)
        self.assertTrue(self.org in response.context["orgs"])
        self.assertTrue(self.org2 in response.context["orgs"])

        self.org2.is_active = False
        self.org2.save()

        response = self.client.get(chooser_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["orgs"]), 1)
        self.assertTrue(self.org in response.context["orgs"])
        self.assertFalse(self.org2 in response.context["orgs"])

    def test_invitation_model(self):
        invitation = Invitation.objects.create(
            org=self.org, user_group="V", email="norkans7@gmail.com", created_by=self.admin, modified_by=self.admin
        )

        with patch("dash.orgs.models.Invitation.generate_random_string") as mock:
            mock.side_effect = [invitation.secret, "A" * 64]

            second_invitation = Invitation.objects.create(
                org=self.org, user_group="E", email="eric@gmail.com", created_by=self.admin, modified_by=self.admin
            )

            self.assertEqual(second_invitation.secret, "A" * 64)

            invitation.email = None
            self.assertIsNone(invitation.send_email())

    def test_manage_accounts(self):
        manage_accounts_url = reverse("orgs.org_manage_accounts")
        self.editor = self.create_user("Editor")
        self.user = self.create_user("User")

        self.org = self.create_org("uganda", self.admin)

        self.login(self.admin)
        self.admin.set_org(self.org)

        self.org.editors.add(self.editor)
        self.org.administrators.add(self.user)

        response = self.client.get(manage_accounts_url, SERVER_NAME="uganda.ureport.io")

        self.assertEqual(200, response.status_code)

        # we have 12 fields in the form including 9 checkboxes for the three users,
        # an emails field a user group field and 'loc' field.
        self.assertEqual(9, len(response.context["form"].fields))
        self.assertTrue("emails" in response.context["form"].fields)
        self.assertTrue("user_group" in response.context["form"].fields)
        for user in [self.editor, self.user, self.admin]:
            self.assertTrue("administrators_%d" % user.pk in response.context["form"].fields)
            self.assertTrue("editors_%d" % user.pk in response.context["form"].fields)

        self.assertFalse(response.context["form"].fields["emails"].initial)
        self.assertEqual("E", response.context["form"].fields["user_group"].initial)

        post_data = dict()

        # keep all the admins
        post_data["administrators_%d" % self.admin.pk] = "on"
        post_data["administrators_%d" % self.user.pk] = "on"
        post_data["administrators_%d" % self.editor.pk] = "on"

        # add self.editor to editors
        post_data["editors_%d" % self.editor.pk] = "on"
        post_data["user_group"] = "E"

        response = self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(302, response.status_code)

        org = Org.objects.get(pk=self.org.pk)
        self.assertEqual(org.administrators.all().count(), 3)
        self.assertFalse(org.viewers.all())
        self.assertTrue(org.editors.all())
        self.assertEqual(org.editors.all()[0].pk, self.editor.pk)

        # add to post_data an email to invite as admin
        post_data["emails"] = "norkans7gmail.com"
        post_data["user_group"] = "A"
        response = self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertTrue("emails" in response.context["form"].errors)
        self.assertEqual("One of the emails you entered is invalid.", response.context["form"].errors["emails"][0])

        # now post with right email
        post_data["emails"] = "norkans7@gmail.com"
        post_data["user_group"] = "A"
        response = self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")

        # an invitation is created and sent by email
        self.assertEqual(1, Invitation.objects.all().count())
        self.assertTrue(len(mail.outbox) == 1)

        invitation = Invitation.objects.get()

        self.assertEqual(invitation.org, self.org)
        self.assertEqual(invitation.email, "norkans7@gmail.com")
        self.assertEqual(invitation.user_group, "A")

        # pretend our invite was acted on
        Invitation.objects.all().update(is_active=False)

        # send another invitation, different group
        post_data["emails"] = "norkans7@gmail.com"
        post_data["user_group"] = "E"
        self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")

        # old invite should be updated
        new_invite = Invitation.objects.all().first()
        self.assertEqual(1, Invitation.objects.all().count())
        self.assertEqual(invitation.pk, new_invite.pk)
        self.assertEqual("E", new_invite.user_group)
        self.assertEqual(2, len(mail.outbox))
        self.assertTrue(new_invite.is_active)

        # post many emails to the form
        post_data["emails"] = "norbert@nyaruka.com,code@nyaruka.com"
        post_data["user_group"] = "A"
        self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")

        # now 2 new invitations are created and sent
        self.assertEqual(3, Invitation.objects.all().count())
        self.assertEqual(4, len(mail.outbox))

    def test_join(self):
        editor_invitation = Invitation.objects.create(
            org=self.org, user_group="E", email="norkans7@gmail.com", created_by=self.admin, modified_by=self.admin
        )

        self.org2 = self.create_org("kenya", self.admin)
        editor_join_url = reverse("orgs.org_join", args=[editor_invitation.secret])
        self.client.logout()

        # if no user is logged we redirect to the create_login page
        response = self.client.get(editor_join_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(302, response.status_code)
        response = self.client.get(editor_join_url, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(
            response.request["PATH_INFO"], reverse("orgs.org_create_login", args=[editor_invitation.secret])
        )

        # a user is already logged in
        self.invited_editor = self.create_user("InvitedEditor")
        self.login(self.invited_editor)

        with patch("dash.orgs.views.OrgCRUDL.Join.get_object") as mock:
            mock.return_value = None

            response = self.client.get(editor_join_url, follow=True, SERVER_NAME="kenya.ureport.io")
            self.assertEqual(response.request["PATH_INFO"], "/")

        response = self.client.get(editor_join_url, SERVER_NAME="kenya.ureport.io")
        self.assertEqual(302, response.status_code)

        response = self.client.get(editor_join_url, follow=True, SERVER_NAME="kenya.ureport.io")
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.wsgi_request.org, self.org)
        self.assertEqual(response.request["PATH_INFO"], editor_join_url)

        response = self.client.get(editor_join_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(200, response.status_code)

        self.assertEqual(self.org.pk, response.context["org"].pk)
        # we have a form without field except one 'loc'
        self.assertEqual(1, len(response.context["form"].fields))

        post_data = dict()
        response = self.client.post(editor_join_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(200, response.status_code)

        self.assertTrue(self.invited_editor in self.org.editors.all())
        self.assertFalse(Invitation.objects.get(pk=editor_invitation.pk).is_active)

        # test overriding the user home page
        with self.settings(SITE_USER_HOME="/example/home"):
            invitation = Invitation.objects.create(
                org=self.org, user_group="E", email="norkans7@gmail.com", created_by=self.admin, modified_by=self.admin
            )
            join_url = reverse("orgs.org_join", args=[invitation.secret])
            post_data = dict()
            response = self.client.post(join_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
            self.assertEqual(response.request["PATH_INFO"], "/example/home")

    def test_create_login(self):
        admin_invitation = Invitation.objects.create(
            org=self.org, user_group="A", email="norkans7@gmail.com", created_by=self.admin, modified_by=self.admin
        )

        self.org2 = self.create_org("kenya", self.admin)

        admin_create_login_url = reverse("orgs.org_create_login", args=[admin_invitation.secret])
        self.client.logout()

        with patch("dash.orgs.views.OrgCRUDL.CreateLogin.get_object") as mock:
            mock.return_value = None

            response = self.client.get(admin_create_login_url, follow=True, SERVER_NAME="kenya.ureport.io")
            self.assertEqual(response.request["PATH_INFO"], "/")

        response = self.client.get(admin_create_login_url, SERVER_NAME="kenya.ureport.io")
        self.assertEqual(302, response.status_code)

        response = self.client.get(admin_create_login_url, follow=True, SERVER_NAME="kenya.ureport.io")
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.wsgi_request.org, self.org)
        self.assertEqual(response.request["PATH_INFO"], admin_create_login_url)

        response = self.client.get(admin_create_login_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(200, response.status_code)

        self.assertEqual(self.org.pk, response.context["org"].pk)

        # we have a form with 4 fields and one hidden 'loc'
        self.assertEqual(5, len(response.context["form"].fields))
        self.assertTrue("first_name" in response.context["form"].fields)
        self.assertTrue("last_name" in response.context["form"].fields)
        self.assertTrue("email" in response.context["form"].fields)
        self.assertTrue("password" in response.context["form"].fields)

        post_data = dict()
        post_data["first_name"] = "Norbert"
        post_data["last_name"] = "Kwizera"
        post_data["email"] = "norkans7@gmail.com"
        post_data["password"] = "norbert"

        response = self.client.post(admin_create_login_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(200, response.status_code)
        self.assertTrue("form" in response.context)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(User.objects.filter(email="norkans7@gmail.com"))
        self.assertTrue(Invitation.objects.get(pk=admin_invitation.pk).is_active)

        post_data = dict()
        post_data["first_name"] = "Norbert"
        post_data["last_name"] = "Kwizera"
        post_data["email"] = "norkans7@gmail.com"
        post_data["password"] = "norbertkwizeranorbert"

        response = self.client.post(admin_create_login_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(200, response.status_code)

        new_invited_user = User.objects.get(email="norkans7@gmail.com")
        self.assertTrue(new_invited_user in self.org.administrators.all())
        self.assertFalse(Invitation.objects.get(pk=admin_invitation.pk).is_active)

        viewer_invitation = Invitation.objects.create(
            org=self.org, user_group="V", email="norkans7@gmail.com", created_by=self.admin, modified_by=self.admin
        )
        viewer_create_login_url = reverse("orgs.org_create_login", args=[viewer_invitation.secret])

        post_data = dict()
        post_data["first_name"] = "Norbert"
        post_data["last_name"] = "Kwizera"
        post_data["email"] = "norkans7@gmail.com"
        post_data["password"] = "norbertkwizeranorbert"

        response = self.client.post(viewer_create_login_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(200, response.status_code)
        self.assertTrue("form" in response.context)
        self.assertTrue(response.context["form"].errors)
        self.assertTrue(User.objects.filter(email="norkans7@gmail.com"))
        self.assertFalse(Invitation.objects.get(pk=admin_invitation.pk).is_active)
        self.assertTrue(Invitation.objects.get(pk=viewer_invitation.pk).is_active)

    def test_dashorgs_templatetags(self):
        self.assertEqual(display_time("2014-11-04T15:11:34Z", self.org), "Nov 04, 2014 15:11")

        self.org.timezone = zoneinfo.ZoneInfo("Africa/Kigali")
        self.org.save()
        self.assertEqual(display_time("2014-11-04T15:11:34Z", self.org), "Nov 04, 2014 17:11")

        self.assertEqual(display_time("2014-11-04T15:11:34Z", self.org, "%A, %B %d, %Y"), "Tuesday, November 04, 2014")

        self.assertEqual(national_phone("+250788505050"), "0788 505 050")
        self.assertEqual(national_phone("250788505050"), "250788505050")
        self.assertEqual(national_phone("+93700325998"), "070 032 5998")


class OrgBackgroundTest(DashTest):
    def setUp(self):
        super(OrgBackgroundTest, self).setUp()

        self.uganda = self.create_org("uganda", self.admin)
        self.nigeria = self.create_org("nigeria", self.admin)

    def test_org_background(self):
        create_url = reverse("orgs.orgbackground_create")

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 4)
        self.assertTrue("org" not in response.context["form"].fields)

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")

        post_data = dict(name="Orange Pattern", background_type="P", image=upload)
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        uganda_org_bg = OrgBackground.objects.order_by("-pk")[0]
        self.assertEqual(uganda_org_bg.org, self.uganda)
        self.assertEqual(uganda_org_bg.name, "Orange Pattern")

        response = self.client.get(create_url, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 4)
        self.assertTrue("org" not in response.context["form"].fields)

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")

        post_data = dict(name="Orange Pattern", background_type="P", image=upload)
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(response.status_code, 200)
        nigeria_org_bg = OrgBackground.objects.order_by("-pk")[0]
        self.assertEqual(nigeria_org_bg.org, self.nigeria)
        self.assertEqual(nigeria_org_bg.name, "Orange Pattern")

        list_url = reverse("orgs.orgbackground_list")

        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertEqual(response.context["object_list"][0], uganda_org_bg)

        response = self.client.get(list_url, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertEqual(response.context["object_list"][0], nigeria_org_bg)

        uganda_bg_update_url = reverse("orgs.orgbackground_update", args=[uganda_org_bg.pk])
        nigeria_bg_update_url = reverse("orgs.orgbackground_update", args=[nigeria_org_bg.pk])

        response = self.client.get(uganda_bg_update_url, SERVER_NAME="nigeria.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(nigeria_bg_update_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(uganda_bg_update_url, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.request["PATH_INFO"], uganda_bg_update_url)
        self.assertEqual(len(response.context["form"].fields), 5)
        self.assertTrue("org" not in response.context["form"].fields)

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")
        post_data = dict(name="Orange Pattern Updated", background_type="P", image=upload)
        response = self.client.post(uganda_bg_update_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.request["PATH_INFO"], list_url)
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertEqual(response.context["object_list"][0].name, "Orange Pattern Updated")

        self.login(self.superuser)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 5)
        self.assertTrue("org" in response.context["form"].fields)

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")

        post_data = dict(name="Blue Pattern", background_type="P", image=upload)
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertTrue("form" in response.context)
        self.assertTrue("org" in response.context["form"].errors)

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")

        post_data = dict(name="Blue Pattern", background_type="P", image=upload, org=self.uganda.pk)

        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertTrue("form" not in response.context)
        blue_bg = OrgBackground.objects.get(name="Blue Pattern")
        self.assertEqual(blue_bg.org, self.uganda)

        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["object_list"]), OrgBackground.objects.count())

        response = self.client.get(nigeria_bg_update_url, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(response.request["PATH_INFO"], nigeria_bg_update_url)
        self.assertEqual(len(response.context["form"].fields), 5)

        self.clear_uploads()


def test_over_time_window(org, prev_started_on, started_on, prev_results=None):
    """The org task function below will be transformed by @org_task decorator, so easier to mock this"""
    return {}


@org_task("test-task-1", lock_timeout=10)
def test_org_task_1(org):
    pass


@org_task("test-task-2")
def test_org_task_2(org, prev_started_on, started_on):
    return test_over_time_window(org, prev_started_on, started_on)


@org_task("test-task-3")
def test_org_task_3(org, prev_started_on, started_on, prev_results):
    return test_over_time_window(org, prev_started_on, started_on, prev_results)


class OrgTaskTest(DashTest):
    def setUp(self):
        super(OrgTaskTest, self).setUp()

        self.org = self.create_org("uganda", self.admin)

    @patch("test_runner.tests.test_over_time_window")
    def test_org_task(self, mock_over_time_window):
        mock_over_time_window.return_value = {"foo": "bar", "zed": 123}

        # org tasks are invoked with a single org id
        test_org_task_1(self.org.id)
        test_org_task_2(self.org.id)
        test_org_task_3(self.org.id)

        # should now have task states for that org
        task1_state1 = TaskState.objects.get(org=self.org, task_key="test-task-1")
        task2_state1 = TaskState.objects.get(org=self.org, task_key="test-task-2")
        task3_state1 = TaskState.objects.get(org=self.org, task_key="test-task-3")

        task1_timetaken = (task2_state1.ended_on - task2_state1.started_on).total_seconds()

        self.assertIsNotNone(task1_state1.started_on)
        self.assertIsNotNone(task1_state1.ended_on)
        self.assertEqual(task1_state1.last_successfully_started_on, task1_state1.started_on)
        self.assertFalse(task1_state1.is_running())
        self.assertEqual(task1_state1.get_last_results(), None)
        self.assertEqual(task2_state1.get_time_taken(), task1_timetaken)
        self.assertFalse(task1_state1.is_failing)
        self.assertTrue(task1_state1.has_ever_run())

        self.assertIsNotNone(task2_state1.started_on)
        self.assertIsNotNone(task2_state1.ended_on)
        self.assertEqual(task2_state1.last_successfully_started_on, task2_state1.started_on)
        self.assertFalse(task2_state1.is_running())
        self.assertEqual(task2_state1.get_last_results(), {"foo": "bar", "zed": 123})

        self.assertFalse(task2_state1.is_failing)

        self.assertEqual(list(TaskState.get_failing()), [])

        mock_over_time_window.assert_has_calls(
            [
                call(self.org, None, task2_state1.started_on),
                call(self.org, None, task3_state1.started_on, None),
            ]
        )
        mock_over_time_window.reset_mock()

        # running again will update state
        test_org_task_2(self.org.id)
        test_org_task_3(self.org.id)

        task2_state2 = TaskState.objects.get(org=self.org, task_key="test-task-2")
        task3_state2 = TaskState.objects.get(org=self.org, task_key="test-task-3")

        self.assertGreater(task2_state2.started_on, task2_state1.started_on)
        self.assertEqual(task2_state2.last_successfully_started_on, task2_state2.started_on)

        mock_over_time_window.assert_has_calls(
            [
                call(self.org, task2_state1.started_on, task2_state2.started_on),
                call(self.org, task3_state1.started_on, task3_state2.started_on, {"foo": "bar", "zed": 123}),
            ]
        )
        mock_over_time_window.reset_mock()

        mock_over_time_window.side_effect = ValueError("DOH!")

        # test when task throw exception
        self.assertRaises(ValueError, test_org_task_2, self.org.pk)

        task2_state3 = TaskState.objects.get(org=self.org, task_key="test-task-2")

        self.assertGreater(task2_state3.started_on, task2_state2.started_on)
        self.assertGreater(task2_state3.ended_on, task2_state2.ended_on)
        self.assertEqual(task2_state3.last_successfully_started_on, task2_state2.started_on)  # hasn't changed
        self.assertFalse(task2_state3.is_running())
        self.assertEqual(task2_state3.get_last_results(), None)
        self.assertTrue(task2_state3.is_failing)

        self.assertEqual(list(TaskState.get_failing()), [task2_state3])

        mock_over_time_window.assert_called_once_with(self.org, task2_state2.started_on, task2_state3.started_on)
        mock_over_time_window.reset_mock()

        # test when called, again, start time is from last successful run
        self.assertRaises(ValueError, test_org_task_2, self.org.pk)

        state4 = TaskState.objects.get(org=self.org, task_key="test-task-2")

        self.assertGreater(state4.started_on, task2_state3.started_on)
        self.assertGreater(state4.ended_on, task2_state3.ended_on)
        self.assertEqual(state4.last_successfully_started_on, task2_state2.started_on)

        mock_over_time_window.assert_called_once_with(self.org, task2_state2.started_on, state4.started_on)
        mock_over_time_window.reset_mock()

        mock_over_time_window.side_effect = None
        mock_over_time_window.return_value = {"foo": "bar", "zed": 123}

        # disable the task for our org
        TaskState.objects.filter(org=self.org, task_key="test-task-2").update(is_disabled=True)

        test_org_task_2(self.org.pk)

        state5 = TaskState.objects.get(org=self.org, task_key="test-task-2")

        self.assertEqual(state5.started_on, state4.started_on)
        self.assertEqual(state5.last_successfully_started_on, task2_state2.started_on)

        mock_over_time_window.assert_not_called()

        # and finally re-enable the task for our org
        TaskState.objects.filter(org=self.org, task_key="test-task-2").update(is_disabled=False)

        test_org_task_2(self.org.pk)

        state6 = TaskState.objects.get(org=self.org, task_key="test-task-2")

        self.assertGreater(state6.started_on, state4.started_on)
        self.assertGreater(state6.last_successfully_started_on, task2_state2.started_on)

        mock_over_time_window.assert_called_once_with(self.org, task2_state2.started_on, state6.started_on)


class TaskCRUDLTest(DashTest):
    def setUp(self):
        super(TaskCRUDLTest, self).setUp()

        self.org = self.create_org("uganda", self.admin)

    def test_list(self):
        url = reverse("orgs.task_list", args=[])

        task1 = TaskState.get_or_create(self.org, "test-task-1")
        task2 = TaskState.get_or_create(self.org, "test-task-2")

        task2.is_failing = True
        task2.save()

        self.login(self.superuser)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["object_list"]), [task1, task2])

        response = self.client.get(url + "?failing=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["object_list"]), [task2])


class CategoryTest(DashTest):
    def setUp(self):
        super(CategoryTest, self).setUp()
        self.uganda = self.create_org("uganda", self.admin)
        self.nigeria = self.create_org("nigeria", self.admin)

    def test_category_model(self):
        category1 = Category.objects.create(
            name="category 1",
            org=self.uganda,
            image="categories/image.jpg",
            created_by=self.admin,
            modified_by=self.admin,
        )

        self.assertEqual(force_str(category1), "uganda - category 1")
        self.assertEqual(category1.get_label_from_instance(), "uganda - category 1")

        category2 = Category.objects.create(
            name="Освіта", org=self.uganda, image="categories/image.jpg", created_by=self.admin, modified_by=self.admin
        )

        label = category2.get_label_from_instance()
        self.assertEqual(label, "uganda - Освіта")

        Category.objects.filter(pk=category2.pk).update(is_active=False)

        category2 = Category.objects.filter(pk=category2.pk).first()
        label = category2.get_label_from_instance()
        self.assertEqual(label, "uganda - Освіта (Inactive)")

        with self.assertRaises(IntegrityError):
            Category.objects.create(name="category 1", org=self.uganda, created_by=self.admin, modified_by=self.admin)

    def test_category_get_first_image(self):
        category1 = Category.objects.create(
            name="category 1", org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        self.assertIsNone(category1.get_first_image())

        category_image1 = CategoryImage.objects.create(
            category=category1, name="image 1", image=None, created_by=self.admin, modified_by=self.admin
        )

        self.assertEqual(force_str(category_image1), "category 1 - image 1")
        self.assertIsNone(category1.get_first_image())

        category_image1.image = "categories/image.jpg"
        category_image1.is_active = False
        category_image1.save()

        self.assertIsNone(category1.get_first_image())

        category_image1.is_active = True
        category_image1.save()

        self.assertTrue(category1.get_first_image())
        self.assertEqual(category1.get_first_image(), category_image1.image)

    def test_create_category(self):
        create_url = reverse("categories.category_create")

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 2)
        self.assertTrue("org" not in response.context["form"].fields)

        post_data = dict()
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertTrue(response.context["form"].errors)
        self.assertTrue("name" in response.context["form"].errors)

        post_data = dict(name="Health")
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        category = Category.objects.order_by("-pk")[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("categories.category_list"))
        self.assertEqual(category.name, "Health")
        self.assertEqual(category.org, self.uganda)

        self.login(self.superuser)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 3)
        self.assertTrue("org" in response.context["form"].fields)

        post_data = dict(name="Education", org=self.uganda.pk)
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        category = Category.objects.order_by("-pk")[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("categories.category_list"))
        self.assertEqual(category.name, "Education")
        self.assertEqual(category.org, self.uganda)

    def test_list_category(self):
        uganda_health = Category.objects.create(
            name="Health", org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        uganda_education = Category.objects.create(
            name="Education", org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        nigeria_health = Category.objects.create(
            name="Health", org=self.nigeria, created_by=self.admin, modified_by=self.admin
        )

        list_url = reverse("categories.category_list")

        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 2)
        self.assertTrue(nigeria_health not in response.context["object_list"])
        self.assertTrue(uganda_health in response.context["object_list"])
        self.assertTrue(uganda_education in response.context["object_list"])

        response = self.client.get(list_url, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertTrue(uganda_health not in response.context["object_list"])
        self.assertTrue(uganda_education not in response.context["object_list"])
        self.assertTrue(nigeria_health in response.context["object_list"])
        self.assertEqual(len(response.context["fields"]), 3)

        self.login(self.superuser)
        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["fields"]), 4)
        self.assertEqual(len(response.context["object_list"]), 2)
        self.assertTrue(uganda_health in response.context["object_list"])
        self.assertTrue(uganda_education in response.context["object_list"])
        self.assertTrue(nigeria_health not in response.context["object_list"])

    def test_category_update(self):
        uganda_health = Category.objects.create(
            name="Health", org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        nigeria_health = Category.objects.create(
            name="Health", org=self.nigeria, created_by=self.admin, modified_by=self.admin
        )

        uganda_update_url = reverse("categories.category_update", args=[uganda_health.pk])
        nigeria_update_url = reverse("categories.category_update", args=[nigeria_health.pk])

        response = self.client.get(uganda_update_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)

        response = self.client.get(uganda_update_url, SERVER_NAME="nigeria.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(nigeria_update_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(uganda_update_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 3)

        post_data = dict(name="Sanitation", is_active=True)
        response = self.client.post(uganda_update_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.request["PATH_INFO"], reverse("categories.category_list"))
        category = Category.objects.get(pk=uganda_health.pk)
        self.assertEqual(category.name, "Sanitation")

    def test_create_category_image(self):
        uganda_health = Category.objects.create(
            name="Health", org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        nigeria_health = Category.objects.create(
            name="Health", org=self.nigeria, created_by=self.admin, modified_by=self.admin
        )

        create_url = reverse("categories.categoryimage_create")

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(create_url, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 4)
        self.assertEqual(response.context["form"].fields["category"].choices.queryset.count(), 1)
        self.assertIsInstance(response.context["form"].fields["category"].choices.field, CategoryChoiceField)
        self.assertEqual(nigeria_health, response.context["form"].fields["category"].choices.queryset[0])

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 4)
        self.assertEqual(response.context["form"].fields["category"].choices.queryset.count(), 1)
        self.assertEqual(uganda_health, response.context["form"].fields["category"].choices.queryset[0])

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")
        post_data = dict(name="health hero", image=upload, category=uganda_health.pk)
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        cat_image = CategoryImage.objects.order_by("-pk")[0]
        self.assertEqual(cat_image.name, "health hero")
        self.assertEqual(cat_image.category, uganda_health)

        list_url = reverse("categories.categoryimage_list")

        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertTrue(cat_image in response.context["object_list"])

        response = self.client.get(list_url, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 0)
        self.assertTrue(cat_image not in response.context["object_list"])

        update_url = reverse("categories.categoryimage_update", args=[cat_image.pk])

        response = self.client.get(update_url, SERVER_NAME="nigeria.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(update_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["form"].fields), 5)

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")
        post_data = dict(name="health image", image=upload, category=uganda_health.pk, is_active=True)
        response = self.client.post(update_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.request["PATH_INFO"], reverse("categories.categoryimage_list"))
        cat_image = CategoryImage.objects.filter(pk=cat_image.pk)[0]
        self.assertEqual(cat_image.name, "health image")

        nigeria_law = Category.objects.create(
            name="Law", org=self.nigeria, is_active=False, created_by=self.admin, modified_by=self.admin
        )

        response = self.client.get(create_url, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 4)
        self.assertEqual(response.context["form"].fields["category"].choices.queryset.count(), 2)
        self.assertIsInstance(response.context["form"].fields["category"].choices.field, CategoryChoiceField)
        self.assertEqual(nigeria_health, response.context["form"].fields["category"].choices.queryset[0])
        self.assertEqual(nigeria_law, response.context["form"].fields["category"].choices.queryset[1])
        self.assertEqual(
            list(response.context["form"].fields["category"].choices),
            [("", "---------"), (nigeria_health.pk, "nigeria - Health"), (nigeria_law.pk, "nigeria - Law (Inactive)")],
        )

        self.clear_uploads()


class StoryTest(DashTest):
    def setUp(self):
        super(StoryTest, self).setUp()
        self.uganda = self.create_org("uganda", self.admin)
        self.nigeria = self.create_org("nigeria", self.admin)

        self.health_uganda = Category.objects.create(
            org=self.uganda, name="Health", created_by=self.admin, modified_by=self.admin
        )

        self.education_nigeria = Category.objects.create(
            org=self.nigeria, name="Education", created_by=self.admin, modified_by=self.admin
        )

    def test_format_audio_link(self):
        self.assertEqual(Story.format_audio_link(""), "")
        self.assertEqual(Story.format_audio_link("http://"), "")
        self.assertEqual(Story.format_audio_link("example.com/foo.mp3"), "http://example.com/foo.mp3")
        self.assertEqual(Story.format_audio_link("http://example.com/foo.mp3"), "http://example.com/foo.mp3")
        self.assertEqual(Story.format_audio_link("https://example.com/foo.mp3"), "https://example.com/foo.mp3")

    def test_story_model(self):
        self.story = Story.objects.create(
            title="Story 1", content="content " * 20, org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        self.assertEqual(self.story.teaser(self.story.summary, 30), "")
        self.assertEqual(self.story.teaser(self.story.content, 30), self.story.content)

        self.story.content = "content " * 250
        self.story.save()

        self.assertEqual(self.story.teaser(self.story.summary, 30), "")
        self.assertEqual(self.story.teaser(self.story.content, 30), "content " * 30 + "..")
        self.assertEqual(self.story.long_teaser(), "content " * 100 + "..")
        self.assertEqual(self.story.short_teaser(), "content " * 40 + "..")

        self.story.summary = "summary " * 150
        self.story.save()

        self.assertEqual(self.story.long_teaser(), "summary " * 100 + "..")
        self.assertEqual(self.story.short_teaser(), "summary " * 40 + "..")

        self.assertIsNone(self.story.get_written_by())

        self.admin.last_name = "Musk"
        self.admin.save()

        self.assertEqual(self.story.get_written_by(), "Musk")

        self.admin.first_name = "Elon"
        self.admin.save()

        self.assertEqual(self.story.get_written_by(), "Elon Musk")

        self.story.written_by = "Trevor Noah"
        self.story.save()

        self.assertEqual(self.story.get_written_by(), "Trevor Noah")

        story_image_1 = StoryImage.objects.create(
            name="image 1", story=self.story, image="", created_by=self.admin, modified_by=self.admin
        )

        self.assertFalse(self.story.get_featured_images())

        story_image_1.image = "stories/someimage.jpg"
        story_image_1.is_active = False
        story_image_1.save()

        self.assertFalse(self.story.get_featured_images())

        story_image_1.is_active = True
        story_image_1.save()

        self.assertTrue(self.story.get_featured_images())
        self.assertEqual(len(self.story.get_featured_images()), 1)
        self.assertTrue(story_image_1 in self.story.get_featured_images())

        self.assertEqual(self.story.get_category_image(), "stories/someimage.jpg")
        self.assertEqual(self.story.get_image(), "stories/someimage.jpg")

        self.story.category = self.health_uganda
        self.story.save()

        self.assertEqual(self.story.get_category_image(), "stories/someimage.jpg")
        self.assertEqual(self.story.get_image(), "stories/someimage.jpg")

        CategoryImage.objects.create(
            category=self.health_uganda,
            name="image 1",
            image="categories/some_image.jpg",
            created_by=self.admin,
            modified_by=self.admin,
        )

        self.assertEqual(self.story.get_category_image(), "categories/some_image.jpg")
        self.assertEqual(self.story.get_image(), "stories/someimage.jpg")

        story_image_1.is_active = False
        story_image_1.save()

        self.assertEqual(self.story.get_category_image(), "categories/some_image.jpg")
        self.assertEqual(self.story.get_image(), "categories/some_image.jpg")

        self.health_uganda.is_active = False
        self.health_uganda.save()

        self.assertFalse(self.story.get_category_image())
        self.assertFalse(self.story.get_image(), "categories/some_image.jpg")

    def test_upload_attachment(self):
        create_url = reverse("stories.story_create")
        self.login(self.admin)

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")
        post_data = dict(
            title="foo",
            content="bar",
            category=self.health_uganda.pk,
            attachment=upload,
            featured=True,
            summary="baz",
            audio_link="example.com/foo.mp3",
            video_id="yt_id",
            tags="   first SECOND third",
            written_by="Content Provider",
        )

        response = self.client.post(create_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertTrue(response.context["form"].errors)
        errors = response.context["form"].errors
        self.assertTrue("attachment" in errors)
        self.assertEqual(errors["attachment"][0], "Only PDF files are supported.")

        upload = open("%s/doc.pdf" % settings.TESTFILES_DIR, "rb")
        post_data = dict(
            title="foo",
            content="bar",
            category=self.health_uganda.pk,
            attachment=upload,
            featured=True,
            summary="baz",
            audio_link="example.com/foo.mp3",
            video_id="yt_id",
            tags="   first SECOND third",
            written_by="Content Provider",
        )

        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        story = Story.objects.get()
        self.assertEqual(response.request["PATH_INFO"], reverse("stories.story_images", args=[story.pk]))
        self.assertEqual(story.title, "foo")
        self.assertEqual(story.content, "bar")
        self.assertEqual(story.category, self.health_uganda)
        self.assertTrue(story.featured)
        self.assertEqual(story.summary, "baz")
        self.assertEqual(story.written_by, "Content Provider")
        self.assertEqual(story.audio_link, "http://example.com/foo.mp3")
        self.assertEqual(story.video_id, "yt_id")
        self.assertEqual(story.tags, " first second third ")

    def test_create_story(self):
        create_url = reverse("stories.story_create")

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(create_url, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        self.login(self.admin)
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(create_url, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertEqual(len(fields), 11)
        self.assertTrue("loc" in fields)
        self.assertTrue("title" in fields)
        self.assertTrue("featured" in fields)
        self.assertTrue("summary" in fields)
        self.assertTrue("content" in fields)
        self.assertTrue("attachment" in fields)
        self.assertTrue("written_by" in fields)
        self.assertTrue("audio_link" in fields)
        self.assertTrue("video_id" in fields)
        self.assertTrue("tags" in fields)
        self.assertTrue("category" in fields)

        self.assertIsInstance(fields["category"].choices.field, CategoryChoiceField)
        self.assertEqual(len(fields["category"].choices.queryset), 1)

        response = self.client.post(create_url, dict(), SERVER_NAME="uganda.ureport.io")
        self.assertTrue(response.context["form"].errors)
        errors = response.context["form"].errors
        self.assertTrue("title" in errors)
        self.assertTrue("content" in errors)
        self.assertTrue("category" in errors)

        post_data = dict(
            title="foo",
            content="bar",
            category=self.health_uganda.pk,
            featured=True,
            summary="baz",
            audio_link="example.com/foo.mp3",
            video_id="yt_id",
            tags="   first SECOND third",
            written_by="Content Provider",
        )

        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        story = Story.objects.get()
        self.assertEqual(response.request["PATH_INFO"], reverse("stories.story_images", args=[story.pk]))
        self.assertEqual(story.title, "foo")
        self.assertEqual(story.content, "bar")
        self.assertEqual(story.category, self.health_uganda)
        self.assertTrue(story.featured)
        self.assertEqual(story.summary, "baz")
        self.assertEqual(story.written_by, "Content Provider")
        self.assertEqual(story.audio_link, "http://example.com/foo.mp3")
        self.assertEqual(story.video_id, "yt_id")
        self.assertEqual(story.tags, " first second third ")

        nigeria_law = Category.objects.create(
            name="Law", org=self.nigeria, is_active=False, created_by=self.admin, modified_by=self.admin
        )

        response = self.client.get(create_url, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].fields["category"].choices.queryset.count(), 2)
        self.assertIsInstance(response.context["form"].fields["category"].choices.field, CategoryChoiceField)
        self.assertEqual(self.education_nigeria, response.context["form"].fields["category"].choices.queryset[0])
        self.assertEqual(nigeria_law, response.context["form"].fields["category"].choices.queryset[1])
        self.assertEqual(
            list(response.context["form"].fields["category"].choices),
            [
                ("", "---------"),
                (self.education_nigeria.pk, "nigeria - Education"),
                (nigeria_law.pk, "nigeria - Law (Inactive)"),
            ],
        )

    def test_update_story(self):
        story1 = Story.objects.create(
            title="foo",
            content="bar",
            category=self.health_uganda,
            org=self.uganda,
            created_by=self.admin,
            modified_by=self.admin,
        )

        story2 = Story.objects.create(
            title="foo",
            content="bar",
            category=self.education_nigeria,
            org=self.nigeria,
            created_by=self.admin,
            modified_by=self.admin,
        )

        update_url_uganda = reverse("stories.story_update", args=[story1.pk])
        update_url_nigeria = reverse("stories.story_update", args=[story2.pk])

        response = self.client.get(update_url_uganda)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(update_url_uganda, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        response = self.client.get(update_url_nigeria)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(update_url_nigeria, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        response = self.client.get(update_url_uganda, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(update_url_nigeria, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(update_url_uganda)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(update_url_uganda, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        response = self.client.get(update_url_nigeria)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(update_url_nigeria, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        response = self.client.get(update_url_nigeria, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(update_url_uganda, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields

        self.assertEqual(len(fields), 12)
        self.assertTrue("loc" in fields)
        self.assertTrue("is_active" in fields)
        self.assertTrue("title" in fields)
        self.assertTrue("featured" in fields)
        self.assertTrue("summary" in fields)
        self.assertTrue("content" in fields)
        self.assertTrue("attachment" in fields)
        self.assertTrue("written_by" in fields)
        self.assertTrue("audio_link" in fields)
        self.assertTrue("video_id" in fields)
        self.assertTrue("tags" in fields)
        self.assertTrue("category" in fields)
        self.assertEqual(len(fields["category"].choices.queryset), 1)

        response = self.client.post(update_url_uganda, dict(), SERVER_NAME="uganda.ureport.io")

        self.assertTrue(response.context["form"].errors)
        errors = response.context["form"].errors
        self.assertTrue("title" in errors)
        self.assertTrue("content" in errors)

        post_data = dict(
            title="foo updated",
            content="bar updated",
            category=self.health_uganda.pk,
            featured=True,
            summary="baz updated",
            video_id="yt_idUpdated",
            tags="   first SECOND third UPDATED",
            audio_link="http://example.com/bar.mp3",
            written_by="Trevor Noah",
        )
        response = self.client.post(update_url_uganda, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        updated_story = Story.objects.get(pk=story1.pk)
        self.assertEqual(response.request["PATH_INFO"], reverse("stories.story_list"))

        self.assertEqual(updated_story.title, "foo updated")
        self.assertEqual(updated_story.content, "bar updated")
        self.assertEqual(updated_story.category, self.health_uganda)
        self.assertTrue(updated_story.featured)
        self.assertEqual(updated_story.summary, "baz updated")
        self.assertEqual(updated_story.written_by, "Trevor Noah")
        self.assertEqual(updated_story.audio_link, "http://example.com/bar.mp3")
        self.assertEqual(updated_story.video_id, "yt_idUpdated")
        self.assertEqual(updated_story.tags, " first second third updated ")

    def test_list_stories(self):
        story1 = Story.objects.create(
            title="foo",
            content="bar",
            category=self.health_uganda,
            org=self.uganda,
            created_by=self.admin,
            modified_by=self.admin,
        )

        story2 = Story.objects.create(
            title="foo",
            content="bar",
            category=self.education_nigeria,
            org=self.nigeria,
            created_by=self.admin,
            modified_by=self.admin,
        )

        list_url = reverse("stories.story_list")

        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(list_url, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        self.login(self.admin)
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(list_url, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertIn(story1, response.context["object_list"])
        self.assertNotIn(story2, response.context["object_list"])

        self.assertContains(response, reverse("stories.story_images", args=[story1.pk]))

    def test_images_story(self):
        story1 = Story.objects.create(
            title="foo",
            content="bar",
            category=self.health_uganda,
            org=self.uganda,
            created_by=self.admin,
            modified_by=self.admin,
        )

        story2 = Story.objects.create(
            title="foo",
            content="bar",
            category=self.education_nigeria,
            org=self.nigeria,
            created_by=self.admin,
            modified_by=self.admin,
        )

        images_url_uganda = reverse("stories.story_images", args=[story1.pk])
        images_url_nigeria = reverse("stories.story_images", args=[story2.pk])

        response = self.client.get(images_url_uganda)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(images_url_uganda, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        response = self.client.get(images_url_nigeria)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(images_url_nigeria, follow=True)
        self.assertEqual(response.request["PATH_INFO"], reverse(settings.SITE_CHOOSER_URL_NAME))

        response = self.client.get(images_url_uganda, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(images_url_nigeria, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(images_url_nigeria, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(images_url_uganda, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        self.assertEqual(len(response.context["form"].fields), 3)
        for field in response.context["form"].fields:
            self.assertFalse(response.context["form"].fields[field].initial)

        self.assertFalse(StoryImage.objects.filter(story=story1))

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")
        post_data = dict(image_1=upload)
        response = self.client.post(images_url_uganda, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertTrue(StoryImage.objects.filter(story=story1))
        self.assertEqual(StoryImage.objects.filter(story=story1).count(), 1)

        response = self.client.get(images_url_uganda, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["form"].fields), 3)
        self.assertTrue(response.context["form"].fields["image_1"].initial)

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")
        post_data = dict(image_1=upload)
        response = self.client.post(images_url_uganda, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertTrue(StoryImage.objects.filter(story=story1))
        self.assertEqual(StoryImage.objects.filter(story=story1).count(), 1)

        self.assertEqual(response.request["PATH_INFO"], reverse("stories.story_list"))

        self.clear_uploads()


class DashBlockTypeTest(DashTest):
    def setUp(self):
        super(DashBlockTypeTest, self).setUp()
        self.uganda = self.create_org("uganda", self.admin)
        self.nigeria = self.create_org("nigeria", self.admin)

    def test_create_dashblocktype(self):
        create_url = reverse("dashblocks.dashblocktype_create")

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertEqual(len(fields), 13)

        response = self.client.post(create_url, dict(), SERVER_NAME="uganda.ureport.io")
        self.assertTrue(response.context["form"].errors)
        errors = response.context["form"].errors
        self.assertEqual(len(errors), 2)
        self.assertTrue("name" in errors)
        self.assertTrue("slug" in errors)

        post_data = dict(name="Test Pages", slug="test_pages", description="foo")
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        dashblocktype = DashBlockType.objects.get()
        self.assertEqual(dashblocktype.name, "Test Pages")
        self.assertEqual(dashblocktype.slug, "test_pages")
        self.assertEqual(dashblocktype.description, "foo")
        self.assertFalse(dashblocktype.has_title)
        self.assertFalse(dashblocktype.has_image)
        self.assertFalse(dashblocktype.has_rich_text)
        self.assertFalse(dashblocktype.has_summary)
        self.assertFalse(dashblocktype.has_link)
        self.assertFalse(dashblocktype.has_color)
        self.assertFalse(dashblocktype.has_gallery)
        self.assertFalse(dashblocktype.has_tags)
        self.assertFalse(dashblocktype.has_video)

        self.assertEqual(force_str(dashblocktype), "Test Pages")

    def test_list_dashblocktype(self):
        list_url = reverse("dashblocks.dashblocktype_list")

        dashblock_type = DashBlockType.objects.create(
            name="Test",
            slug="test",
            description="foo",
            has_title=True,
            has_image=True,
            has_rich_text=True,
            has_summary=True,
            has_link=True,
            has_color=False,
            has_video=False,
            has_tags=False,
            has_gallery=False,
            created_by=self.admin,
            modified_by=self.admin,
        )

        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["fields"]), 3)
        self.assertTrue("name" in response.context["fields"])
        self.assertTrue("slug" in response.context["fields"])
        self.assertTrue("description" in response.context["fields"])
        self.assertTrue(dashblock_type in response.context["object_list"])

    def test_update_dashblocktype(self):

        dashblock_type = DashBlockType.objects.create(
            name="Test",
            slug="test",
            description="foo",
            has_title=True,
            has_image=True,
            has_rich_text=True,
            has_summary=True,
            has_link=True,
            has_color=False,
            has_video=False,
            has_tags=False,
            has_gallery=False,
            created_by=self.admin,
            modified_by=self.admin,
        )

        update_url = reverse("dashblocks.dashblocktype_update", args=[dashblock_type.pk])

        response = self.client.get(update_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(update_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(update_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertEqual(len(fields), 14)

        response = self.client.post(update_url, dict(), SERVER_NAME="uganda.ureport.io")
        self.assertTrue(response.context["form"].errors)
        errors = response.context["form"].errors
        self.assertEqual(len(errors), 2)
        self.assertTrue("name" in errors)
        self.assertTrue("slug" in errors)

        post_data = dict(is_active=True, name="foo", slug="bar", description="baz", has_rich_text=True, has_video=True)
        response = self.client.post(update_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertFalse("form" in response.context)
        updated_dashblock_type = DashBlockType.objects.get(pk=dashblock_type.pk)
        self.assertEqual(updated_dashblock_type.name, "foo")
        self.assertEqual(updated_dashblock_type.slug, "bar")
        self.assertEqual(updated_dashblock_type.description, "baz")
        self.assertTrue(updated_dashblock_type.has_rich_text)
        self.assertTrue(updated_dashblock_type.has_video)
        self.assertFalse(updated_dashblock_type.has_title)
        self.assertFalse(updated_dashblock_type.has_summary)
        self.assertFalse(updated_dashblock_type.has_color)
        self.assertFalse(updated_dashblock_type.has_tags)
        self.assertFalse(updated_dashblock_type.has_gallery)


class DashBlockTest(DashTest):
    def setUp(self):
        super(DashBlockTest, self).setUp()
        self.uganda = self.create_org("uganda", self.admin)
        self.nigeria = self.create_org("nigeria", self.admin)

        self.type_foo = DashBlockType.objects.create(
            name="Foo",
            slug="foo",
            description="foo description",
            has_title=True,
            has_image=True,
            has_rich_text=True,
            has_summary=True,
            has_link=True,
            has_color=False,
            has_video=False,
            has_tags=True,
            has_gallery=False,
            created_by=self.admin,
            modified_by=self.admin,
        )

        self.type_bar = DashBlockType.objects.create(
            name="Bar",
            slug="bar",
            description="bar description",
            has_title=False,
            has_image=False,
            has_rich_text=False,
            has_summary=False,
            has_link=False,
            has_color=False,
            has_video=False,
            has_tags=True,
            has_gallery=False,
            created_by=self.admin,
            modified_by=self.admin,
        )

    def test_dashblock_model(self):
        dashblock1 = DashBlock.objects.create(
            dashblock_type=self.type_foo,
            org=self.uganda,
            title="First",
            content="First content",
            summary="first summary",
            created_by=self.admin,
            modified_by=self.admin,
        )

        self.assertEqual(force_str(dashblock1), "First")

        dashblock2 = DashBlock.objects.create(
            dashblock_type=self.type_bar,
            org=self.uganda,
            content="Bar content",
            summary="bar summary here",
            created_by=self.admin,
            modified_by=self.admin,
        )

        self.assertEqual(force_str(dashblock2), "Bar - %d" % dashblock2.pk)

        self.assertEqual(dashblock1.teaser(dashblock1.content, 1), "First ...")
        self.assertEqual(dashblock1.teaser(dashblock1.content, 10), "First content")

        self.assertEqual(dashblock1.long_content_teaser(), "First content")
        self.assertEqual(dashblock1.short_content_teaser(), "First content")
        self.assertEqual(dashblock1.long_summary_teaser(), "first summary")
        self.assertEqual(dashblock1.short_summary_teaser(), "first summary")

        dashblock1.content = "ab " * 150
        dashblock1.summary = "cd " * 120
        dashblock1.save()

        self.assertEqual(dashblock1.long_content_teaser(), "ab " * 100 + "...")
        self.assertEqual(dashblock1.short_content_teaser(), "ab " * 40 + "...")
        self.assertEqual(dashblock1.long_summary_teaser(), "cd " * 100 + "...")
        self.assertEqual(dashblock1.short_summary_teaser(), "cd " * 40 + "...")

    def test_create_dashblock(self):
        create_url = reverse("dashblocks.dashblock_create")

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertEqual(len(fields), 11)
        self.assertTrue("dashblock_type" in fields)
        self.assertTrue("title" in fields)
        self.assertTrue("summary" in fields)
        self.assertTrue("content" in fields)
        self.assertTrue("image" in fields)
        self.assertTrue("color" in fields)
        self.assertTrue("link" in fields)
        self.assertTrue("video_id" in fields)
        self.assertTrue("tags" in fields)
        self.assertTrue("priority" in fields)
        self.assertTrue("loc" in fields)
        self.assertFalse("gallery" in fields)
        self.assertFalse("org" in fields)

        self.assertEqual(fields["priority"].initial, 0)
        self.assertIsNone(response.context["type"])

        response = self.client.post(create_url, dict(), SERVER_NAME="uganda.ureport.io")
        self.assertTrue(response.context["form"].errors)
        self.assertTrue("dashblock_type" in response.context["form"].errors)
        self.assertTrue("priority" in response.context["form"].errors)

        post_data = dict(dashblock_type=self.type_bar.pk, priority=2, tags="   first SECOND four   ")
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")

        dashblock = DashBlock.objects.get()
        self.assertEqual(dashblock.priority, 2)
        self.assertEqual(dashblock.dashblock_type, self.type_bar)
        self.assertEqual(dashblock.tags, " first second four ")

        self.assertEqual(response.request["PATH_INFO"], reverse("dashblocks.dashblock_list"))
        self.assertEqual(response.request["QUERY_STRING"], "type=%d" % self.type_bar.pk)

        response = self.client.get(create_url + "?type=%d" % self.type_bar.pk, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertEqual(len(fields), 4)
        self.assertTrue("tags" in fields)
        self.assertTrue("priority" in fields)
        self.assertTrue("loc" in fields)
        self.assertTrue("content" in fields)
        self.assertTrue(response.context["type"])
        self.assertEqual(response.context["type"], self.type_bar)
        # self.assertEqual(fields['priority'].initial, 3)

        response = self.client.get(create_url + "?type=%d" % self.type_foo.pk, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertEqual(len(fields), 8)
        self.assertTrue("title" in fields)
        self.assertTrue("summary" in fields)
        self.assertTrue("content" in fields)
        self.assertTrue("image" in fields)
        self.assertTrue("link" in fields)
        self.assertTrue("tags" in fields)
        self.assertTrue("priority" in fields)
        self.assertTrue("loc" in fields)
        self.assertFalse("video_id" in fields)
        self.assertFalse("color" in fields)
        self.assertFalse("gallery" in fields)
        self.assertFalse("org" in fields)
        self.assertFalse("dashblock_type" in fields)

        self.assertTrue(response.context["type"])
        self.assertEqual(response.context["type"], self.type_foo)

        post_data = dict(title="kigali", content="kacyiru", tags=" Gasabo KACYIRU Umujyi   ", priority=0)
        response = self.client.post(
            create_url + "?type=%d" % self.type_foo.pk, post_data, follow=True, SERVER_NAME="uganda.ureport.io"
        )
        new_dashblock = DashBlock.objects.get(title="kigali")
        self.assertEqual(new_dashblock.dashblock_type, self.type_foo)
        self.assertEqual(new_dashblock.org, self.uganda)
        self.assertEqual(new_dashblock.tags, " gasabo kacyiru umujyi ")
        self.assertEqual(new_dashblock.title, "kigali")
        self.assertEqual(new_dashblock.content, "kacyiru")

        response = self.client.get(create_url + "?slug=inexistent", SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertTrue("dashblock_type" in fields)
        self.assertFalse(response.context["type"])

    def test_update_dashblock(self):
        dashblock1 = DashBlock.objects.create(
            dashblock_type=self.type_foo,
            org=self.uganda,
            title="First",
            content="First content",
            summary="first summary",
            created_by=self.admin,
            modified_by=self.admin,
        )

        update_url = reverse("dashblocks.dashblock_update", args=[dashblock1.pk])

        response = self.client.get(update_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(update_url, SERVER_NAME="uganda.ureport.io")

        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertEqual(len(fields), 9)
        self.assertTrue("is_active" in fields)
        self.assertTrue("title" in fields)
        self.assertTrue("summary" in fields)
        self.assertTrue("content" in fields)
        self.assertTrue("image" in fields)
        self.assertTrue("link" in fields)
        self.assertTrue("priority" in fields)
        self.assertTrue("loc" in fields)
        self.assertTrue("tags" in fields)
        self.assertFalse("video_id" in fields)
        self.assertFalse("color" in fields)
        self.assertFalse("gallery" in fields)
        self.assertFalse("org" in fields)
        self.assertFalse("dashblock_type" in fields)

        self.assertTrue(response.context["type"])
        self.assertEqual(response.context["type"], self.type_foo)

        response = self.client.post(update_url, dict(), SERVER_NAME="uganda.ureport.io")
        self.assertTrue("form" in response.context)

        self.assertTrue("priority" in response.context["form"].errors)

        post_data = dict(title="kigali", content="kacyiru", tags=" Gasabo KACYIRU Umujyi   ", priority=0)
        response = self.client.post(update_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertFalse("form" in response.context)
        updated_dashblock = DashBlock.objects.get(pk=dashblock1.pk)
        self.assertEqual(updated_dashblock.dashblock_type, self.type_foo)
        self.assertEqual(updated_dashblock.org, self.uganda)
        self.assertEqual(updated_dashblock.tags, " gasabo kacyiru umujyi ")
        self.assertEqual(updated_dashblock.title, "kigali")
        self.assertEqual(updated_dashblock.content, "kacyiru")

        self.type_foo.has_tags = False
        self.type_foo.save()

        response = self.client.get(update_url, SERVER_NAME="uganda.ureport.io")

        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertEqual(len(fields), 8)
        self.assertTrue("is_active" in fields)
        self.assertTrue("title" in fields)
        self.assertTrue("summary" in fields)
        self.assertTrue("content" in fields)
        self.assertTrue("image" in fields)
        self.assertTrue("link" in fields)
        self.assertTrue("priority" in fields)
        self.assertTrue("loc" in fields)
        self.assertFalse("dashblock_type" in fields)
        self.assertFalse("video_id" in fields)
        self.assertFalse("color" in fields)
        self.assertFalse("gallery" in fields)
        self.assertFalse("org" in fields)
        self.assertFalse("tags" in fields)

        self.login(self.superuser)
        response = self.client.get(update_url, SERVER_NAME="uganda.ureport.io")

        self.assertEqual(response.status_code, 200)
        self.assertTrue("form" in response.context)
        fields = response.context["form"].fields
        self.assertEqual(len(fields), 9)
        self.assertTrue("is_active" in fields)
        self.assertTrue("title" in fields)
        self.assertTrue("summary" in fields)
        self.assertTrue("content" in fields)
        self.assertTrue("image" in fields)
        self.assertTrue("link" in fields)
        self.assertTrue("priority" in fields)
        self.assertTrue("loc" in fields)
        self.assertTrue("dashblock_type" in fields)
        self.assertFalse("video_id" in fields)
        self.assertFalse("color" in fields)
        self.assertFalse("gallery" in fields)
        self.assertFalse("org" in fields)
        self.assertFalse("tags" in fields)

        post_data = dict(title="Gasabo", content="gasabo", priority=0, dashblock_type=self.type_foo.pk)

        response = self.client.post(update_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertFalse("form" in response.context)
        updated_dashblock = DashBlock.objects.get(pk=dashblock1.pk)
        self.assertEqual(updated_dashblock.dashblock_type, self.type_foo)
        self.assertEqual(updated_dashblock.org, self.uganda)
        self.assertEqual(updated_dashblock.title, "Gasabo")
        self.assertEqual(updated_dashblock.content, "gasabo")

    def test_list_dashblock(self):
        list_url = reverse("dashblocks.dashblock_list")

        dashblock1 = DashBlock.objects.create(
            dashblock_type=self.type_foo,
            org=self.uganda,
            title="First",
            content="First content",
            summary="first summary",
            created_by=self.admin,
            modified_by=self.admin,
        )

        dashblock2 = DashBlock.objects.create(
            dashblock_type=self.type_bar,
            org=self.uganda,
            content="Bar content",
            summary="bar summary here",
            created_by=self.admin,
            modified_by=self.admin,
        )

        dashblock3 = DashBlock.objects.create(
            dashblock_type=self.type_foo,
            org=self.nigeria,
            title="third",
            content="third content",
            summary="third summary",
            created_by=self.admin,
            modified_by=self.admin,
        )

        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["object_list"]), 2)
        self.assertIn(dashblock1, response.context["object_list"])
        self.assertIn(dashblock2, response.context["object_list"])
        self.assertNotIn(dashblock3, response.context["object_list"])
        self.assertEqual(len(response.context["fields"]), 4)
        self.assertIn("tags", response.context["fields"])
        self.assertIn("title", response.context["fields"])
        self.assertIn("dashblock_type", response.context["fields"])
        self.assertIn("priority", response.context["fields"])

        self.assertEqual(len(response.context["types"]), 2)
        self.assertIn(self.type_foo, response.context["types"])
        self.assertIn(self.type_bar, response.context["types"])

        response = self.client.get(list_url + "?type=%d" % self.type_bar.pk, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertNotIn(dashblock1, response.context["object_list"])
        self.assertIn(dashblock2, response.context["object_list"])
        self.assertNotIn(dashblock3, response.context["object_list"])

        self.assertContains(response, force_str(dashblock2))

        self.assertEqual(len(response.context["fields"]), 4)
        self.assertIn("tags", response.context["fields"])
        self.assertIn("title", response.context["fields"])
        self.assertIn("dashblock_type", response.context["fields"])
        self.assertIn("priority", response.context["fields"])
        self.assertEqual(len(response.context["types"]), 2)
        self.assertIn(self.type_foo, response.context["types"])
        self.assertIn(self.type_bar, response.context["types"])

        self.type_bar.has_tags = False
        self.type_bar.save()

        response = self.client.get(list_url + "?type=%d" % self.type_bar.pk, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["fields"]), 3)
        self.assertNotIn("tags", response.context["fields"])
        self.assertIn("title", response.context["fields"])
        self.assertIn("dashblock_type", response.context["fields"])
        self.assertIn("priority", response.context["fields"])

        self.type_bar.is_active = False
        self.type_bar.save()

        response = self.client.get(list_url + "?type=%d" % self.type_bar.pk, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["object_list"])
        self.assertNotIn(dashblock1, response.context["object_list"])
        self.assertNotIn(dashblock2, response.context["object_list"])
        self.assertNotIn(dashblock3, response.context["object_list"])
        self.assertEqual(len(response.context["types"]), 1)
        self.assertIn(self.type_foo, response.context["types"])
        self.assertNotIn(self.type_bar, response.context["types"])

        response = self.client.get(list_url + "?slug=%s" % self.type_foo.slug, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertIn(dashblock1, response.context["object_list"])
        self.assertNotIn(dashblock2, response.context["object_list"])
        self.assertNotIn(dashblock3, response.context["object_list"])
        self.assertEqual(response.context["filtered_type"], self.type_foo)
        self.assertEqual(len(response.context["types"]), 1)
        self.assertIn(self.type_foo, response.context["types"])
        self.assertNotIn(self.type_bar, response.context["types"])

    def test_dashblock_image(self):
        dashblock1 = DashBlock.objects.create(
            dashblock_type=self.type_foo,
            org=self.uganda,
            title="First",
            content="First content",
            summary="first summary",
            created_by=self.admin,
            modified_by=self.admin,
        )

        create_url = reverse("dashblocks.dashblockimage_create") + "?dashblock=%d" % dashblock1.pk

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertTrue("form" in response.context)

        response = self.client.post(create_url, dict(), SERVER_NAME="uganda.ureport.io")
        self.assertTrue(response.context["form"].errors)

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")
        post_data = dict(dashblock=dashblock1.pk, image=upload, caption="image caption")

        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        dashblock_image = DashBlockImage.objects.get()

        self.assertEqual(dashblock_image.dashblock, dashblock1)
        self.assertEqual(dashblock_image.caption, "image caption")

        self.assertEqual(response.request["PATH_INFO"], reverse("dashblocks.dashblock_update", args=[dashblock1.pk]))

        update_url = reverse("dashblocks.dashblockimage_update", args=[dashblock_image.pk])

        upload = open("%s/image.jpg" % settings.TESTFILES_DIR, "rb")
        post_data = dict(dashblock=dashblock1.pk, image=upload, caption="image updated caption")
        response = self.client.post(update_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")

        self.assertEqual(DashBlockImage.objects.count(), 1)
        updated_block_image = DashBlockImage.objects.get(pk=dashblock_image.pk)
        self.assertEqual(updated_block_image.caption, "image updated caption")
        self.assertEqual(response.request["PATH_INFO"], reverse("dashblocks.dashblock_update", args=[dashblock1.pk]))

        list_url = reverse("dashblocks.dashblockimage_list")
        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertTrue(updated_block_image in response.context["object_list"])

        self.clear_uploads()

    def test_template_tags(self):
        dashblock1 = DashBlock.objects.create(
            dashblock_type=self.type_foo,
            org=self.uganda,
            title="First",
            content="First content",
            summary="first summary",
            created_by=self.admin,
            modified_by=self.admin,
        )

        dashblock2 = DashBlock.objects.create(
            dashblock_type=self.type_bar,
            org=self.uganda,
            content="Bar content",
            summary="bar summary here",
            created_by=self.admin,
            modified_by=self.admin,
        )

        dashblock3 = DashBlock.objects.create(
            dashblock_type=self.type_foo,
            org=self.nigeria,
            title="third",
            content="third content",
            summary="third summary",
            created_by=self.admin,
            modified_by=self.admin,
        )

        context = dict()
        self.assertEqual(load_qbs(context, None, ""), "")
        self.assertFalse(context)

        self.assertEqual(
            load_qbs(context, self.uganda, "invalid_slug"),
            getattr(
                settings,
                "DASHBLOCK_STRING_IF_INVALID",
                '<b><font color="red">DashBlockType with slug: %s not found</font></b>',
            )
            % "invalid_slug",
        )
        self.assertFalse(context)

        self.assertEqual(load_qbs(context, self.uganda, "foo"), "")
        self.assertTrue(context)
        self.assertTrue("foo" in context)
        self.assertTrue(dashblock1 in context["foo"])
        self.assertFalse(dashblock2 in context["foo"])
        self.assertFalse(dashblock3 in context["foo"])

        dashblock4 = DashBlock.objects.create(
            dashblock_type=self.type_foo,
            org=self.uganda,
            title="Fourth",
            content="Fourth content",
            summary="fourth summary",
            created_by=self.admin,
            modified_by=self.admin,
        )

        dashblock1.tags = " kigali gasabo "
        dashblock1.save()

        dashblock4.tags = " kigali kacyiru "
        dashblock4.save()

        self.assertEqual(load_qbs(context, self.uganda, "foo"), "")
        self.assertTrue(context)
        self.assertTrue("foo" in context)
        self.assertTrue(dashblock1 in context["foo"])
        self.assertFalse(dashblock2 in context["foo"])
        self.assertFalse(dashblock3 in context["foo"])
        self.assertTrue(dashblock4 in context["foo"])

        self.assertEqual(load_qbs(context, self.uganda, "foo", "kigali"), "")
        self.assertTrue(context)
        self.assertTrue("foo" in context)
        self.assertTrue(dashblock1 in context["foo"])
        self.assertFalse(dashblock2 in context["foo"])
        self.assertFalse(dashblock3 in context["foo"])
        self.assertTrue(dashblock4 in context["foo"])

        self.assertEqual(load_qbs(context, self.uganda, "foo", "gasabo"), "")
        self.assertTrue(context)
        self.assertTrue("foo" in context)
        self.assertTrue(dashblock1 in context["foo"])
        self.assertFalse(dashblock2 in context["foo"])
        self.assertFalse(dashblock3 in context["foo"])
        self.assertFalse(dashblock4 in context["foo"])


class TemplateTagsTest(DashTest):
    def test_if_url(self):
        url = reverse("testapp.contact_test_tags")

        response = self.client.get(url)

        self.assertContains(response, "TAG1-YES")
        self.assertNotContains(response, "TAG1-NO")
        self.assertNotContains(response, "TAG2-YES")
        self.assertContains(response, "TAG2-NO")


class TagTest(DashTest):
    def setUp(self):
        super(TagTest, self).setUp()
        self.uganda = self.create_org("uganda", self.admin)
        self.nigeria = self.create_org("nigeria", self.admin)

    def test_tag_model(self):
        tag1 = Tag.objects.create(name="tag 1", org=self.uganda, created_by=self.admin, modified_by=self.admin)

        self.assertEqual(force_str(tag1), "tag 1")

        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="tag 1", org=self.uganda, created_by=self.admin, modified_by=self.admin)

    def test_create_tag(self):
        create_url = reverse("tags.tag_create")

        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 2)
        self.assertNotIn("org", response.context["form"].fields)

        post_data = dict()
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertTrue(response.context["form"].errors)
        self.assertIn("name", response.context["form"].errors)

        post_data = dict(name="Health")
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        tag = Tag.objects.order_by("-pk")[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("tags.tag_list"))
        self.assertEqual(tag.name, "Health")
        self.assertEqual(tag.org, self.uganda)

        self.login(self.superuser)
        response = self.client.get(create_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 2)
        self.assertNotIn("org", response.context["form"].fields)

        post_data = dict(name="Education")
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        tag = Tag.objects.order_by("-pk")[0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("tags.tag_list"))
        self.assertEqual(tag.name, "Education")
        self.assertEqual(tag.org, self.uganda)

    def test_list_tags(self):
        uganda_health_tag = Tag.objects.create(
            name="Health", org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        uganda_education_tag = Tag.objects.create(
            name="Education", org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        nigeria_health_tag = Tag.objects.create(
            name="Health", org=self.nigeria, created_by=self.admin, modified_by=self.admin
        )

        list_url = reverse("tags.tag_list")

        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 2)
        self.assertNotIn(nigeria_health_tag, response.context["object_list"])
        self.assertIn(uganda_health_tag, response.context["object_list"])
        self.assertIn(uganda_education_tag, response.context["object_list"])

        response = self.client.get(list_url, SERVER_NAME="nigeria.ureport.io")
        self.assertEqual(len(response.context["object_list"]), 1)
        self.assertNotIn(uganda_health_tag, response.context["object_list"])
        self.assertNotIn(uganda_education_tag, response.context["object_list"])
        self.assertIn(nigeria_health_tag, response.context["object_list"])
        self.assertEqual(len(response.context["fields"]), 3)

        self.login(self.superuser)
        response = self.client.get(list_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(len(response.context["fields"]), 3)
        self.assertEqual(len(response.context["object_list"]), 2)
        self.assertIn(uganda_health_tag, response.context["object_list"])
        self.assertIn(uganda_education_tag, response.context["object_list"])
        self.assertNotIn(nigeria_health_tag, response.context["object_list"])

    def test_tag_update(self):
        uganda_health_tag = Tag.objects.create(
            name="Health", org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        nigeria_health_tag = Tag.objects.create(
            name="Health", org=self.nigeria, created_by=self.admin, modified_by=self.admin
        )

        uganda_update_url = reverse("tags.tag_update", args=[uganda_health_tag.pk])
        nigeria_update_url = reverse("tags.tag_update", args=[nigeria_health_tag.pk])

        response = self.client.get(uganda_update_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)

        response = self.client.get(uganda_update_url, SERVER_NAME="nigeria.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(nigeria_update_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(uganda_update_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields), 2)

        post_data = dict(name="Sanitation", is_active=True)
        response = self.client.post(uganda_update_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.request["PATH_INFO"], reverse("tags.tag_list"))
        tag = Tag.objects.get(pk=uganda_health_tag.pk)
        self.assertEqual(tag.name, "Sanitation")

    def test_tag_delete(self):
        uganda_health_tag = Tag.objects.create(
            name="Health", org=self.uganda, created_by=self.admin, modified_by=self.admin
        )

        nigeria_health_tag = Tag.objects.create(
            name="Health", org=self.nigeria, created_by=self.admin, modified_by=self.admin
        )

        uganda_delete_url = reverse("tags.tag_delete", args=[uganda_health_tag.pk])
        nigeria_delete_url = reverse("tags.tag_delete", args=[nigeria_health_tag.pk])

        response = self.client.get(uganda_delete_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.post(uganda_delete_url, {"id": uganda_health_tag.pk}, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        self.login(self.admin)

        response = self.client.get(uganda_delete_url, SERVER_NAME="nigeria.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(nigeria_delete_url, SERVER_NAME="uganda.ureport.io")
        self.assertLoginRedirect(response)

        response = self.client.get(uganda_delete_url, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(uganda_delete_url, {"id": uganda_health_tag.pk}, SERVER_NAME="uganda.ureport.io")
        self.assertEqual(response.status_code, 302)

        self.assertFalse(Tag.objects.filter(pk=uganda_health_tag.pk))
