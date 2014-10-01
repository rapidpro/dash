from __future__ import unicode_literals

from datetime import datetime
import json
import urllib
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.http import HttpRequest
import pytz
from smartmin.tests import SmartminTest
from dash.api import API
from dash.orgs.middleware import SetOrgMiddleware
from dash.orgs.models import Org, OrgBackground, Invitation
from django.core.exceptions import DisallowedHost

from mock import patch, Mock
from django.utils import timezone
from dash.orgs.views import OrgPermsMixin


class UserTest(SmartminTest):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="super", email="super@user.com", password="super")

        self.admin = self.create_user("Administrator")

    def test_user_profile(self):
        profile_url = reverse('users.user_profile', args=[self.admin.pk])

        response = self.client.get(profile_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(profile_url)
        self.assertEquals(response.status_code, 200)
        self.assertTrue('form' in response.context)

        post_data = dict(username='denzel@nyaruka.com', first_name='Denzel', last_name='Washington',
                         email='washington@nyaruka.com', old_password='Administrator',
                         new_password='Washington2', confirm_new_password='Washington2')

        response = self.client.post(profile_url, post_data, follow=True)

        new_admin = User.objects.get(pk=self.admin.pk)
        self.assertEquals(new_admin.username, 'washington@nyaruka.com')
        self.assertEquals(new_admin.email, 'washington@nyaruka.com')
        self.assertFalse(User.objects.filter(username='denzel@nyaruka.com'))





class DashTest(SmartminTest):

    def setUp(self):
        self.superuser = User.objects.create_superuser(username="super", email="super@user.com", password="super")

        self.admin = self.create_user("Administrator")


    def create_org(self, subdomain, user):

        email = subdomain + "@user.com"
        first_name = subdomain + "_First"
        last_name = subdomain + "_Last"
        name = subdomain

        orgs = Org.objects.filter(subdomain=subdomain)
        if orgs:
            org =orgs[0]
            org.name = name
            org.save()
        else:
            org = Org.objects.create(subdomain=subdomain, name=name, language='en', created_by=user, modified_by=user)

        org.administrators.add(user)

        self.assertEquals(Org.objects.filter(subdomain=subdomain).count(), 1)
        return Org.objects.get(subdomain=subdomain)


    def read_json(self, filename):
        from django.conf import settings
        handle = open('%s/test_api/%s.json' % (settings.MEDIA_ROOT, filename))
        contents = handle.read()
        handle.close()
        return contents

class SetOrgMiddlewareTest(DashTest):

    def setUp(self):
        super(SetOrgMiddlewareTest, self).setUp()

        self.middleware = SetOrgMiddleware()
        self.request = Mock(spec=HttpRequest)
        self.request.user = User.objects.get(pk=-1)
        self.request.path = '/'
        self.request.get_host.return_value="ureport.io"
        self.request.META = dict(HTTP_HOST=None)

    def test_process_request_without_org(self):
        response = self.middleware.process_request(self.request)
        self.assertEqual(response.template_name, settings.SITE_CHOOSER_TEMPLATE)
        self.assertFalse(response.context_data['orgs'])

    def test_process_request_with_org(self):

        ug_org = self.create_org('uganda', self.admin)
        ug_dash_url = ug_org.subdomain + ".ureport.io"
        self.request.get_host.return_value=ug_dash_url

        response = self.middleware.process_request(self.request)
        self.assertEqual(response, None)
        self.assertEqual(self.request.org, ug_org)

        self.request.user = self.admin
        response = self.middleware.process_request(self.request)
        self.assertEqual(response, None)
        self.assertEqual(self.request.org, ug_org)
        self.assertEquals(self.request.user.get_org(), ug_org)

        # test invalid subdomain
        wrong_subdomain_url = "blabla.ureport.io"
        self.request.get_host.return_value=wrong_subdomain_url
        response = self.middleware.process_request(self.request)
        self.assertEqual(response.template_name, settings.SITE_CHOOSER_TEMPLATE)
        self.assertEquals(len(response.context_data['orgs']), 1)
        self.assertEquals(response.context_data['orgs'][0], ug_org)
        self.assertEqual(self.request.org, None)
        self.assertEquals(self.request.user.get_org(), None)

        rw_org = self.create_org('rwanda', self.admin)
        wrong_subdomain_url = "blabla.ureport.io"
        self.request.get_host.return_value=wrong_subdomain_url
        response = self.middleware.process_request(self.request)
        self.assertEqual(response.template_name, settings.SITE_CHOOSER_TEMPLATE)
        self.assertEquals(len(response.context_data['orgs']), 2)
        self.assertTrue(rw_org in response.context_data['orgs'])
        self.assertTrue(ug_org in response.context_data['orgs'])

        self.request.get_host.side_effect = DisallowedHost
        response = self.middleware.process_request(self.request)
        self.assertEqual(response.template_name, settings.SITE_CHOOSER_TEMPLATE)
        self.assertEquals(len(response.context_data['orgs']), 2)
        self.assertTrue(rw_org in response.context_data['orgs'])
        self.assertTrue(ug_org in response.context_data['orgs'])

class OrgTest(DashTest):

    def setUp(self):
        super(OrgTest, self).setUp()

        self.org = self.create_org("uganda", self.admin)

    def test_org_model(self):
        user = self.create_user("User")

        self.assertEquals(self.org.__unicode__(), 'uganda')


        self.assertIsNone(Org.get_org(None))
        self.assertEquals(Org.get_org(self.admin), self.org)
        self.assertIsNone(Org.get_org(user))

        new_user = Org.create_user('email@example.com', 'secretpassword')
        self.assertIsInstance(new_user, User)
        self.assertEquals(new_user.email, "email@example.com")
        self.assertEquals(new_user.username, "email@example.com")
        self.assertTrue(new_user.check_password("secretpassword"))

        api = self.org.get_api()
        self.assertIsInstance(api, API)
        self.assertEquals(api.org, self.org)

        self.assertEquals(self.org.get_user(), self.admin)

        viewer = self.create_user('Viewer')
        editor = self.create_user('Editor')
        self.org.viewers.add(viewer)
        self.org.editors.add(editor)

        self.assertTrue(self.org.get_user_org_group(self.admin))
        self.assertEquals(self.org.get_user_org_group(self.admin).name, "Administrators")
        self.assertTrue(self.org.get_user_org_group(editor))
        self.assertEquals(self.org.get_user_org_group(editor).name, "Editors")
        self.assertTrue(self.org.get_user_org_group(viewer))
        self.assertEquals(self.org.get_user_org_group(viewer).name, "Viewers")
        self.assertIsNone(self.org.get_user_org_group(user))

        org_users = self.org.get_org_users()
        self.assertEquals(len(org_users), 3)
        self.assertIn(self.admin, org_users)
        self.assertIn(editor, org_users)
        self.assertIn(viewer, org_users)

        org_admins = self.org.get_org_admins()
        self.assertEquals(len(org_admins), 1)
        self.assertIn(self.admin, org_admins)

        org_editors = self.org.get_org_editors()
        self.assertEquals(len(org_editors), 1)
        self.assertIn(editor, org_editors)

        org_viewers = self.org.get_org_viewers()
        self.assertEquals(len(org_viewers), 1)
        self.assertIn(viewer, org_viewers)

        self.assertIsNone(self.org.get_config('field_name'))
        self.org.set_config('field_name', 'field_value')
        self.assertEquals(self.org.get_config('field_name'), 'field_value')

        self.org.set_config('other_field_name', 'other_value')
        self.assertEquals(self.org.get_config('field_name'), 'field_value')
        self.assertEquals(self.org.get_config('other_field_name'), 'other_value')

        self.org._config = None
        self.assertEquals(self.org.get_config('field_name'), 'field_value')
        self.assertEquals(self.org.get_config('other_field_name'), 'other_value')

    def test_get_most_active_regions(self):
        self.org.set_config('gender_label', 'Gender')

        with patch('dash.api.API.get_contact_field_results') as mock:
            mock.return_value = [dict(label='LABEL_1', set=15, unset=5),
                                 dict(label='LABEL_2', set=100, unset=200),
                                 dict(label='LABEL_3', set=50, unset=30)]

            self.assertEquals(self.org.get_most_active_regions(), ['LABEL_2', 'LABEL_3', 'LABEL_1'])
            mock.assert_called_once_with('Gender', dict(location='State'))

    def test_organize_categories_data(self):

        self.org.set_config('born_label', "Born")
        self.org.set_config('registration_label', "Registration")
        self.org.set_config('occupation_label', "Occupation")

        self.assertEquals(self.org.organize_categories_data('random_field', []), [])
        self.assertEquals(self.org.organize_categories_data('born', []), [])
        self.assertEquals(self.org.organize_categories_data('registration', []), [])
        self.assertEquals(self.org.organize_categories_data('occupation', []), [])
        self.assertEquals(self.org.organize_categories_data('random_field', ['random_api_data']), ['random_api_data'])

        tz = pytz.timezone('Africa/Kigali')
        with patch.object(timezone, 'now', return_value=tz.localize(datetime(2014, 9, 26, 10, 20, 30, 40))):

            self.assertEquals(self.org.organize_categories_data('born', [dict(categories=[])]), [dict(categories=[])])
            self.assertEquals(self.org.organize_categories_data('born', [dict(categories=[dict(label='123', count=50)])]), [dict(categories=[])])
            self.assertEquals(self.org.organize_categories_data('born', [dict(categories=[dict(label='12345', count=50)])]), [dict(categories=[])])
            self.assertEquals(self.org.organize_categories_data('born', [dict(categories=[dict(label='abcd', count=50)])]), [dict(categories=[])])
            self.assertEquals(self.org.organize_categories_data('born', [dict(categories=[dict(label='1899', count=50)])]), [dict(categories=[])])

            self.assertEquals(self.org.organize_categories_data('born', [dict(categories=[dict(label='2010', count=50)])]),
                              [dict(categories=[dict(label='0-10', count=50)])])

            self.assertEquals(self.org.organize_categories_data('born', [dict(categories=[dict(label='2000', count=50)])]),
                              [dict(categories=[dict(label='10-20', count=50)])])


            born_api_data = [dict(categories=[dict(label='1700', count=10),
                                              dict(label='1998', count=10),
                                              dict(label='123', count=10),
                                              dict(label='abcd', count=1),
                                              dict(label='2005', count=50),
                                              dict(label='97675', count=10),
                                              dict(label='1990', count=20),
                                              dict(label='1995', count=5),
                                              dict(label='2009', count=30),
                                              dict(label='2001', count=10),
                                              dict(label='2011', count=25)])]

            expected_born_data = [dict(categories=[dict(label='0-10', count=105),
                                                   dict(label='10-20', count=25),
                                                   dict(label='20-30', count=20)])]

            self.assertEquals(self.org.organize_categories_data('born', born_api_data), expected_born_data)

            self.assertEquals(self.org.organize_categories_data('registration', [dict(categories=[])]), [dict(categories=[{'count': 0, 'label': '03/24/14'}, {'count': 0, 'label': '03/31/14'}, {'count': 0, 'label': '04/07/14'}, {'count': 0, 'label': '04/14/14'}, {'count': 0, 'label': '04/21/14'}, {'count': 0, 'label': '04/28/14'}, {'count': 0, 'label': '05/05/14'}, {'count': 0, 'label': '05/12/14'}, {'count': 0, 'label': '05/19/14'}, {'count': 0, 'label': '05/26/14'}, {'count': 0, 'label': '06/02/14'}, {'count': 0, 'label': '06/09/14'}, {'count': 0, 'label': '06/16/14'}, {'count': 0, 'label': '06/23/14'}, {'count': 0, 'label': '06/30/14'}, {'count': 0, 'label': '07/07/14'}, {'count': 0, 'label': '07/14/14'}, {'count': 0, 'label': '07/21/14'}, {'count': 0, 'label': '07/28/14'}, {'count': 0, 'label': '08/04/14'}, {'count': 0, 'label': '08/11/14'}, {'count': 0, 'label': '08/18/14'}, {'count': 0, 'label': '08/25/14'}, {'count': 0, 'label': '09/01/14'}, {'count': 0, 'label': '09/08/14'}, {'count': 0, 'label': '09/15/14'}, {'count': 0, 'label': '09/22/14'}])])
            self.assertEquals(self.org.organize_categories_data('registration', [dict(categories=[dict(label='26-9-2013 21:30', count=20)])]), [dict(categories=[{'count': 0, 'label': '03/24/14'}, {'count': 0, 'label': '03/31/14'}, {'count': 0, 'label': '04/07/14'}, {'count': 0, 'label': '04/14/14'}, {'count': 0, 'label': '04/21/14'}, {'count': 0, 'label': '04/28/14'}, {'count': 0, 'label': '05/05/14'}, {'count': 0, 'label': '05/12/14'}, {'count': 0, 'label': '05/19/14'}, {'count': 0, 'label': '05/26/14'}, {'count': 0, 'label': '06/02/14'}, {'count': 0, 'label': '06/09/14'}, {'count': 0, 'label': '06/16/14'}, {'count': 0, 'label': '06/23/14'}, {'count': 0, 'label': '06/30/14'}, {'count': 0, 'label': '07/07/14'}, {'count': 0, 'label': '07/14/14'}, {'count': 0, 'label': '07/21/14'}, {'count': 0, 'label': '07/28/14'}, {'count': 0, 'label': '08/04/14'}, {'count': 0, 'label': '08/11/14'}, {'count': 0, 'label': '08/18/14'}, {'count': 0, 'label': '08/25/14'}, {'count': 0, 'label': '09/01/14'}, {'count': 0, 'label': '09/08/14'}, {'count': 0, 'label': '09/15/14'}, {'count': 0, 'label': '09/22/14'}])])
            self.assertEquals(self.org.organize_categories_data('registration', [dict(categories=[dict(label='31-3-2014 21:30', count=20)])]),
                              [dict(categories=[{'count': 0, 'label': '03/24/14'}, {'count': 20, 'label': '03/31/14'}, {'count': 0, 'label': '04/07/14'}, {'count': 0, 'label': '04/14/14'}, {'count': 0, 'label': '04/21/14'}, {'count': 0, 'label': '04/28/14'}, {'count': 0, 'label': '05/05/14'}, {'count': 0, 'label': '05/12/14'}, {'count': 0, 'label': '05/19/14'}, {'count': 0, 'label': '05/26/14'}, {'count': 0, 'label': '06/02/14'}, {'count': 0, 'label': '06/09/14'}, {'count': 0, 'label': '06/16/14'}, {'count': 0, 'label': '06/23/14'}, {'count': 0, 'label': '06/30/14'}, {'count': 0, 'label': '07/07/14'}, {'count': 0, 'label': '07/14/14'}, {'count': 0, 'label': '07/21/14'}, {'count': 0, 'label': '07/28/14'}, {'count': 0, 'label': '08/04/14'}, {'count': 0, 'label': '08/11/14'}, {'count': 0, 'label': '08/18/14'}, {'count': 0, 'label': '08/25/14'}, {'count': 0, 'label': '09/01/14'}, {'count': 0, 'label': '09/08/14'}, {'count': 0, 'label': '09/15/14'}, {'count': 0, 'label': '09/22/14'}])])

            self.assertEquals(self.org.organize_categories_data('registration', [dict(categories=[dict(label='31-3-2014 21:30', count=20),
                                                                                                  dict(label='3-4-2014 20:54',  count=15)])]),
                              [dict(categories=[{'count': 0, 'label': '03/24/14'}, {'count': 35, 'label': '03/31/14'}, {'count': 0, 'label': '04/07/14'}, {'count': 0, 'label': '04/14/14'}, {'count': 0, 'label': '04/21/14'}, {'count': 0, 'label': '04/28/14'}, {'count': 0, 'label': '05/05/14'}, {'count': 0, 'label': '05/12/14'}, {'count': 0, 'label': '05/19/14'}, {'count': 0, 'label': '05/26/14'}, {'count': 0, 'label': '06/02/14'}, {'count': 0, 'label': '06/09/14'}, {'count': 0, 'label': '06/16/14'}, {'count': 0, 'label': '06/23/14'}, {'count': 0, 'label': '06/30/14'}, {'count': 0, 'label': '07/07/14'}, {'count': 0, 'label': '07/14/14'}, {'count': 0, 'label': '07/21/14'}, {'count': 0, 'label': '07/28/14'}, {'count': 0, 'label': '08/04/14'}, {'count': 0, 'label': '08/11/14'}, {'count': 0, 'label': '08/18/14'}, {'count': 0, 'label': '08/25/14'}, {'count': 0, 'label': '09/01/14'}, {'count': 0, 'label': '09/08/14'}, {'count': 0, 'label': '09/15/14'}, {'count': 0, 'label': '09/22/14'}])])

            self.assertEquals(self.org.organize_categories_data('registration', [dict(categories=[dict(label='31-3-2014 21:30', count=20),
                                                                                                  dict(label='3-4-2014 20:54',  count=15),
                                                                                                  dict(label='8-4-2014 18:43', count=10)])]),
                              [dict(categories=[{'count': 0, 'label': '03/24/14'}, {'count': 35, 'label': '03/31/14'}, {'count': 10, 'label': '04/07/14'}, {'count': 0, 'label': '04/14/14'}, {'count': 0, 'label': '04/21/14'}, {'count': 0, 'label': '04/28/14'}, {'count': 0, 'label': '05/05/14'}, {'count': 0, 'label': '05/12/14'}, {'count': 0, 'label': '05/19/14'}, {'count': 0, 'label': '05/26/14'}, {'count': 0, 'label': '06/02/14'}, {'count': 0, 'label': '06/09/14'}, {'count': 0, 'label': '06/16/14'}, {'count': 0, 'label': '06/23/14'}, {'count': 0, 'label': '06/30/14'}, {'count': 0, 'label': '07/07/14'}, {'count': 0, 'label': '07/14/14'}, {'count': 0, 'label': '07/21/14'}, {'count': 0, 'label': '07/28/14'}, {'count': 0, 'label': '08/04/14'}, {'count': 0, 'label': '08/11/14'}, {'count': 0, 'label': '08/18/14'}, {'count': 0, 'label': '08/25/14'}, {'count': 0, 'label': '09/01/14'}, {'count': 0, 'label': '09/08/14'}, {'count': 0, 'label': '09/15/14'}, {'count': 0, 'label': '09/22/14'}])])

            self.assertEquals(self.org.organize_categories_data('registration', [dict(categories=[dict(label='31-3-2014 21:30', count=20),
                                                                                                  dict(label='3-4-2014 20:54',  count=15),
                                                                                                  dict(label='8-4-2014 18:43', count=10),
                                                                                                  dict(label='10-10-2014 12:54', count=100)])]),
                              [dict(categories=[{'count': 0, 'label': '03/24/14'}, {'count': 35, 'label': '03/31/14'}, {'count': 10, 'label': '04/07/14'}, {'count': 0, 'label': '04/14/14'}, {'count': 0, 'label': '04/21/14'}, {'count': 0, 'label': '04/28/14'}, {'count': 0, 'label': '05/05/14'}, {'count': 0, 'label': '05/12/14'}, {'count': 0, 'label': '05/19/14'}, {'count': 0, 'label': '05/26/14'}, {'count': 0, 'label': '06/02/14'}, {'count': 0, 'label': '06/09/14'}, {'count': 0, 'label': '06/16/14'}, {'count': 0, 'label': '06/23/14'}, {'count': 0, 'label': '06/30/14'}, {'count': 0, 'label': '07/07/14'}, {'count': 0, 'label': '07/14/14'}, {'count': 0, 'label': '07/21/14'}, {'count': 0, 'label': '07/28/14'}, {'count': 0, 'label': '08/04/14'}, {'count': 0, 'label': '08/11/14'}, {'count': 0, 'label': '08/18/14'}, {'count': 0, 'label': '08/25/14'}, {'count': 0, 'label': '09/01/14'}, {'count': 0, 'label': '09/08/14'}, {'count': 0, 'label': '09/15/14'}, {'count': 0, 'label': '09/22/14'}])])

            self.assertEquals(self.org.organize_categories_data('occupation', [dict(categories=[])]), [dict(categories=[])])
            self.assertEquals(self.org.organize_categories_data('occupation', [dict(categories=[dict(label='All Responses', count=20)])]), [dict(categories=[])])
            self.assertEquals(self.org.organize_categories_data('occupation', [dict(categories=[dict(label='All Responses', count=20),
                                                                                                dict(label='Student', count=50)])]), [dict(categories=[dict(label='Student', count=50)])])

            self.assertEquals(self.org.organize_categories_data('occupation', [dict(categories=[dict(label='Student', count=500),
                                                                                                dict(label='Player', count=300),
                                                                                                dict(label='Journalist', count=50),
                                                                                                dict(label='Actor', count=30),
                                                                                                dict(label='Manager', count=150),
                                                                                                dict(label='All Responses', count=20),
                                                                                                dict(label='Teacher', count=10),
                                                                                                dict(label='Officer', count=8),
                                                                                                dict(label='Nurse', count=5),
                                                                                                dict(label='Cameraman', count=5),
                                                                                                dict(label='Writer', count=3),
                                                                                                dict(label='Photographer', count=2),
                                                                                                dict(label='DJ', count=1),
                                                                                                dict(label='Mechanic', count=1),
                                                                                                dict(label='Engineer', count=1),
                                                                                                dict(label='Professor', count=1)])]),


                              [dict(categories=[dict(label='Student', count=500),
                                                dict(label='Player', count=300),
                                                dict(label='Journalist', count=50),
                                                dict(label='Actor', count=30),
                                                dict(label='Manager', count=150),
                                                dict(label='Teacher', count=10),
                                                dict(label='Officer', count=8),
                                                dict(label='Nurse', count=5),
                                                dict(label='Cameraman', count=5)
                                               ])])

    def test_org_create(self):
        create_url = reverse("orgs.org_create")

        response = self.client.get(create_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(create_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(create_url)
        self.assertEquals(200, response.status_code)
        self.assertFalse(Org.objects.filter(name="kLab"))
        self.assertEquals(User.objects.all().count(), 3)

        user_alice = User.objects.create_user("alicefox")

        data = dict(name="kLab", subdomain="klab", administrators=[user_alice.pk])
        response = self.client.post(create_url, data, follow=True)
        self.assertTrue('form' not in response.context)
        self.assertTrue(Org.objects.filter(name="kLab"))
        org = Org.objects.get(name="kLab")
        self.assertEquals(User.objects.all().count(), 4)
        self.assertTrue(org.administrators.filter(username="alicefox"))


    def test_org_update(self):
        update_url = reverse("orgs.org_update", args=[self.org.pk])

        response = self.client.get(update_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(update_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(update_url)
        self.assertEquals(200, response.status_code)
        self.assertFalse(Org.objects.filter(name="Burundi"))
        self.assertEquals(len(response.context['form'].fields), 8)

        post_data = dict(name="Burundi", subdomain="burundi", is_active=True, male_label="male", female_label='female', administrators=self.admin.pk)
        response = self.client.post(update_url, post_data)
        self.assertEquals(response.status_code, 302)

        response = self.client.post(update_url, post_data, follow=True)
        self.assertEquals(response.status_code, 200)
        org = Org.objects.get(pk=self.org.pk)
        self.assertEquals(org.name, "Burundi")
        self.assertEquals(org.subdomain, "burundi")
        self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_list'))

    def test_org_list(self):
        list_url = reverse("orgs.org_list")

        response = self.client.get(list_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(list_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(list_url)
        self.assertEquals(response.status_code, 200)
        self.assertTrue(response.context['object_list'])
        self.assertTrue(self.org in response.context['object_list'])
        self.assertEquals(len(response.context['fields']), 3)

    def test_org_choose(self):
        choose_url = reverse('orgs.org_choose')

        Org.objects.all().delete()

        response = self.client.get(choose_url)
        self.assertLoginRedirect(response)

        self.login(self.superuser)
        response = self.client.get(choose_url)
        self.assertEquals(response.status_code, 302)
        response = self.client.get(choose_url, follow=True)
        self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_list'))

        self.login(self.admin)
        response = self.client.get(choose_url)
        self.assertEquals(response.status_code, 302)
        response = self.client.get(choose_url, follow=True)
        self.assertEquals(response.request['PATH_INFO'], reverse('users.user_login'))

        self.org = self.create_org("uganda", self.admin)

        # with a subdomain
        response = self.client.get(choose_url, SERVER_NAME='uganda.ureport.io')
        self.assertEquals(response.status_code, 302)
        response = self.client.get(choose_url, follow=True, SERVER_NAME='uganda.ureport.io')
        self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_home'))

        # without subdomain
        response = self.client.get(choose_url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_choose'))
        self.assertEquals(len(response.context['orgs']), 1)
        self.assertTrue(self.org in response.context['orgs'])
        self.assertFalse('org' in response.context)
        self.assertTrue('form' in response.context)
        self.assertEquals(len(response.context['form'].fields), 2)
        self.assertTrue('organization' in response.context['form'].fields)
        self.assertTrue('loc' in response.context['form'].fields)

        org_choices = response.context['form'].fields['organization'].choices.queryset
        self.assertEquals(len(org_choices), 1)
        self.assertTrue(self.org in org_choices)

        post_data = dict(organization=self.org.pk)
        response = self.client.post(choose_url, post_data, follow=True)
        self.assertTrue('org' in response.context)
        self.assertEquals(self.org, response.context['org'])
        self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_home'))

        user = self.create_user('user')
        other_org = self.create_org('other', user)

        post_data = dict(organization=other_org.pk)
        response = self.client.post(choose_url, post_data, follow=True)
        self.assertFalse('org' in response.context)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].errors)
        self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_choose'))

        self.nigeria = self.create_org('nigeria', self.admin)

        response = self.client.get(choose_url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_choose'))
        self.assertEquals(len(response.context['orgs']), 2)
        self.assertTrue(self.org in response.context['orgs'])
        self.assertTrue(self.nigeria in response.context['orgs'])
        self.assertFalse(other_org in response.context['orgs'])
        self.assertFalse('org' in response.context)
        self.assertTrue('form' in response.context)
        self.assertEquals(len(response.context['form'].fields), 2)
        self.assertTrue('organization' in response.context['form'].fields)
        self.assertTrue('loc' in response.context['form'].fields)

        org_choices = response.context['form'].fields['organization'].choices.queryset
        self.assertEquals(len(org_choices), 2)
        self.assertTrue(self.org in org_choices)
        self.assertTrue(self.nigeria in org_choices)

        post_data = dict(organization=self.nigeria.pk)
        response = self.client.post(choose_url, post_data, follow=True)
        self.assertTrue('org' in response.context)
        self.assertEquals(self.nigeria, response.context['org'])
        self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_home'))


    def test_org_home(self):
        home_url = reverse('orgs.org_home')

        response = self.client.get(home_url)
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(home_url, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(200, response.status_code)
        self.assertEquals(response.context['object'], self.org)
        self.assertEquals(response.context['org'], self.org)
        self.assertTrue('Not Set' in response.content)

        self.org.api_token = '0' * 64
        self.org.save()

        self.login(self.admin)
        response = self.client.get(home_url, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(200, response.status_code)
        self.assertEquals(response.context['object'], self.org)
        self.assertEquals(response.context['org'], self.org)
        self.assertFalse('Not Set' in response.content)
        self.assertTrue('*' * 32 in response.content)


    def test_org_edit(self):

        with patch('dash.orgs.models.API') as mock:
            mock.return_value.get_country_geojson.return_value = dict(type="FeatureCollection",
                                                                      features=[dict(type='Feature',
                                                                                     properties=dict(id="R3713501",
                                                                                                     level=1,
                                                                                                     name="Abia"),
                                                                                     geometry=dict(type="MultiPolygon",
                                                                                                   coordinates=[[[[7, 5]]]]
                                                                                                   )
                                                                                     )
                                                                      ])



            edit_url = reverse("orgs.org_edit")

            self.login(self.admin)
            self.admin.set_org(self.org)

            response = self.client.get(edit_url, SERVER_NAME="uganda.ureport.io")
            self.assertEquals(response.status_code, 200)
            self.assertTrue(response.context['form'])
            self.assertEquals(len(response.context['form'].fields), 10)

            # featured state is currently disabled; adjust the following lines
            self.assertTrue('featured_state' not in response.context['form'].fields) # this make sure the featured state are disabled
            # self.assertEquals(len(response.context['form'].fields['featured_state'].choices), 1)
            # self.assertEquals(response.context['form'].fields['featured_state'].choices[0][0], 'R3713501')
            # self.assertEquals(response.context['form'].fields['featured_state'].choices[0][1], 'Abia')


            self.assertEquals(response.context['form'].initial['name'], 'uganda')
            self.assertEquals(response.context['object'], self.org)
            self.assertEquals(response.context['object'], response.context['org'])
            self.assertEquals(response.context['object'].subdomain, 'uganda')

            post_data = dict()
            response = self.client.post(edit_url, post_data, SERVER_NAME="uganda.ureport.io")
            self.assertTrue(response.context['form'])

            errors = response.context['form'].errors
            self.assertEquals(len(errors.keys()), 2)
            self.assertTrue('name' in errors)
            self.assertTrue('shortcode' in errors)
            self.assertEquals(errors['name'][0], 'This field is required.')
            self.assertEquals(errors['shortcode'][0], 'This field is required.')

            post_data = dict(name="Rwanda",
                             shortcode="224433",
                             featured_state="R3713501")

            response = self.client.post(edit_url, post_data, SERVER_NAME="uganda.ureport.io")
            self.assertEquals(response.status_code, 302)

            response = self.client.post(edit_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
            self.assertFalse('form' in response.context)
            org = Org.objects.get(pk=self.org.pk)
            self.assertEquals(org.name, "Rwanda")
            self.assertEquals(org.get_config('shortcode'), "224433")


            # featured state is currenty disabled, adjust the following lines
            self.assertFalse(org.get_config('featured_state')) # this make sure the featured state are disabled
            #self.assertEquals(org.get_config('featured_state'), "R3713501")

            self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_home'))

            response = self.client.get(edit_url, SERVER_NAME="uganda.ureport.io")
            self.assertEquals(response.status_code, 200)
            form = response.context['form']
            self.assertEquals(form.initial['shortcode'], "224433")
            self.assertEquals(form.initial['name'], "Rwanda")

    def test_invitation_model(self):
        invitation = Invitation.objects.create(org=self.org,
                                               user_group="V",
                                               email="norkans7@gmail.com",
                                               created_by=self.admin,
                                               modified_by=self.admin)

        with patch('dash.orgs.models.Invitation.generate_random_string') as mock:
            mock.side_effect = [invitation.secret, 'A' * 64]

            second_invitation = Invitation.objects.create(org=self.org,
                                                          user_group="E",
                                                          email="eric@gmail.com",
                                                          created_by=self.admin,
                                                          modified_by=self.admin)

            self.assertEquals(second_invitation.secret, 'A' * 64)

            invitation.email = None
            self.assertIsNone(invitation.send_email())



    def test_manage_accounts(self):
        manage_accounts_url = reverse('orgs.org_manage_accounts')
        self.editor = self.create_user("Editor")
        self.user = self.create_user("User")

        self.org = self.create_org("uganda", self.admin)

        self.login(self.admin)
        self.admin.set_org(self.org)

        self.org.editors.add(self.editor)
        self.org.administrators.add(self.user)


        response = self.client.get(manage_accounts_url, SERVER_NAME="uganda.ureport.io")

        self.assertEquals(200, response.status_code)

        # we have 12 fields in the form including 9 checkboxes for the three users, an emails field a user group field and 'loc' field.
        self.assertEquals(12, len(response.context['form'].fields))
        self.assertTrue('emails' in response.context['form'].fields)
        self.assertTrue('user_group' in response.context['form'].fields)
        for user in [self.editor, self.user, self.admin]:
            self.assertTrue("administrators_%d" % user.pk in response.context['form'].fields)
            self.assertTrue("editors_%d" % user.pk in response.context['form'].fields)
            self.assertTrue("viewers_%d" % user.pk in response.context['form'].fields)

        self.assertFalse(response.context['form'].fields['emails'].initial)
        self.assertEquals('V', response.context['form'].fields['user_group'].initial)

        post_data = dict()

        # keep all the admins
        post_data['administrators_%d' % self.admin.pk] = 'on'
        post_data['administrators_%d' % self.user.pk] = 'on'
        post_data['administrators_%d' % self.editor.pk] = 'on'

        # add self.editor to editors
        post_data['editors_%d' % self.editor.pk] = 'on'
        post_data['user_group'] = 'E'

        response = self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(302, response.status_code)

        org = Org.objects.get(pk=self.org.pk)
        self.assertEquals(org.administrators.all().count(), 3)
        self.assertFalse(org.viewers.all())
        self.assertTrue(org.editors.all())
        self.assertEquals(org.editors.all()[0].pk, self.editor.pk)

        # add to post_data an email to invite as admin
        post_data['emails'] = "norkans7gmail.com"
        post_data['user_group'] = 'A'
        response = self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertTrue('emails' in response.context['form'].errors)
        self.assertEquals("One of the emails you entered is invalid.", response.context['form'].errors['emails'][0])

        # now post with right email
        post_data['emails'] = "norkans7@gmail.com"
        post_data['user_group'] = 'A'
        response = self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")

        # an invitation is created and sent by email
        self.assertEquals(1, Invitation.objects.all().count())
        self.assertTrue(len(mail.outbox) == 1)

        invitation = Invitation.objects.get()

        self.assertEquals(invitation.org, self.org)
        self.assertEquals(invitation.email, "norkans7@gmail.com")
        self.assertEquals(invitation.user_group, "A")

        # pretend our invite was acted on
        Invitation.objects.all().update(is_active=False)

        # send another invitation, different group
        post_data['emails'] = "norkans7@gmail.com"
        post_data['user_group'] = 'E'
        self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")

        # old invite should be updated
        new_invite = Invitation.objects.all().first()
        self.assertEquals(1, Invitation.objects.all().count())
        self.assertEquals(invitation.pk, new_invite.pk)
        self.assertEquals('E', new_invite.user_group)
        self.assertEquals(2, len(mail.outbox))
        self.assertTrue(new_invite.is_active)


        # post many emails to the form
        post_data['emails'] = "norbert@nyaruka.com,code@nyaruka.com"
        post_data['user_group'] = 'A'
        self.client.post(manage_accounts_url, post_data, SERVER_NAME="uganda.ureport.io")

        # now 2 new invitations are created and sent
        self.assertEquals(3, Invitation.objects.all().count())
        self.assertEquals(4, len(mail.outbox))

    def test_join(self):
        editor_invitation = Invitation.objects.create(org=self.org,
                                               user_group="E",
                                               email="norkans7@gmail.com",
                                               created_by=self.admin,
                                               modified_by=self.admin)

        self.org2 = self.create_org("kenya", self.admin)
        editor_join_url = reverse('orgs.org_join', args=[editor_invitation.secret])
        self.client.logout()

        # if no user is logged we redirect to the create_login page
        response = self.client.get(editor_join_url, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(302, response.status_code)
        response = self.client.get(editor_join_url, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(response.request['PATH_INFO'], reverse('orgs.org_create_login', args=[editor_invitation.secret]))

        # a user is already logged in
        self.invited_editor = self.create_user("InvitedEditor")
        self.login(self.invited_editor)

        with patch('dash.orgs.views.OrgCRUDL.Join.get_object') as mock:
            mock.return_value = None

            response = self.client.get(editor_join_url, follow=True, SERVER_NAME="kenya.ureport.io")
            self.assertEquals(response.request['PATH_INFO'], settings.LOGIN_REDIRECT_URL)

        response = self.client.get(editor_join_url, SERVER_NAME="kenya.ureport.io")
        self.assertEquals(302, response.status_code)


        response = self.client.get(editor_join_url, follow=True, SERVER_NAME="kenya.ureport.io")
        self.assertEquals(200, response.status_code)
        self.assertEquals(response.wsgi_request.org, self.org)
        self.assertEquals(response.request['PATH_INFO'], editor_join_url)

        response = self.client.get(editor_join_url, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(200, response.status_code)

        self.assertEquals(self.org.pk, response.context['org'].pk)
        # we have a form without field except one 'loc'
        self.assertEquals(1, len(response.context['form'].fields))

        post_data = dict()
        response = self.client.post(editor_join_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(200, response.status_code)

        self.assertTrue(self.invited_editor in self.org.editors.all())
        self.assertFalse(Invitation.objects.get(pk=editor_invitation.pk).is_active)

    def test_create_login(self):
        admin_invitation = Invitation.objects.create(org=self.org,
                                                     user_group="A",
                                                     email="norkans7@gmail.com",
                                                     created_by=self.admin,
                                                     modified_by=self.admin)

        self.org2 = self.create_org("kenya", self.admin)

        admin_create_login_url = reverse('orgs.org_create_login', args=[admin_invitation.secret])
        self.client.logout()

        with patch('dash.orgs.views.OrgCRUDL.CreateLogin.get_object') as mock:
            mock.return_value = None

            response = self.client.get(admin_create_login_url, follow=True, SERVER_NAME="kenya.ureport.io")
            self.assertEquals(response.request['PATH_INFO'], settings.LOGIN_REDIRECT_URL)

        response = self.client.get(admin_create_login_url, SERVER_NAME="kenya.ureport.io")
        self.assertEquals(302, response.status_code)

        response = self.client.get(admin_create_login_url, follow=True, SERVER_NAME="kenya.ureport.io")
        self.assertEquals(200, response.status_code)
        self.assertEquals(response.wsgi_request.org, self.org)
        self.assertEquals(response.request['PATH_INFO'], admin_create_login_url)

        response = self.client.get(admin_create_login_url, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(200, response.status_code)

        self.assertEquals(self.org.pk, response.context['org'].pk)

        # we have a form with 4 fields and one hidden 'loc'
        self.assertEquals(5, len(response.context['form'].fields))
        self.assertTrue('first_name' in response.context['form'].fields)
        self.assertTrue('last_name' in response.context['form'].fields)
        self.assertTrue('email' in response.context['form'].fields)
        self.assertTrue('password' in response.context['form'].fields)


        post_data = dict()
        post_data['first_name'] = "Norbert"
        post_data['last_name'] = "Kwizera"
        post_data['email'] = "norkans7@gmail.com"
        post_data['password'] = "norbert"

        response = self.client.post(admin_create_login_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(200, response.status_code)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(User.objects.filter(email='norkans7@gmail.com'))
        self.assertTrue(Invitation.objects.get(pk=admin_invitation.pk).is_active)

        post_data = dict()
        post_data['first_name'] = "Norbert"
        post_data['last_name'] = "Kwizera"
        post_data['email'] = "norkans7@gmail.com"
        post_data['password'] = "norbertkwizeranorbert"

        response = self.client.post(admin_create_login_url, post_data, follow=True, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(200, response.status_code)

        new_invited_user = User.objects.get(email="norkans7@gmail.com")
        self.assertTrue(new_invited_user in self.org.administrators.all())
        self.assertFalse(Invitation.objects.get(pk=admin_invitation.pk).is_active)

        viewer_invitation = Invitation.objects.create(org=self.org,
                                                      user_group="V",
                                                      email="norkans7@gmail.com",
                                                      created_by=self.admin,
                                                      modified_by=self.admin)
        viewer_create_login_url = reverse('orgs.org_create_login', args=[viewer_invitation.secret])

        post_data = dict()
        post_data['first_name'] = "Norbert"
        post_data['last_name'] = "Kwizera"
        post_data['email'] = "norkans7@gmail.com"
        post_data['password'] = "norbertkwizeranorbert"

        response = self.client.post(viewer_create_login_url, post_data, SERVER_NAME="uganda.ureport.io")
        self.assertEquals(200, response.status_code)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].errors)
        self.assertTrue(User.objects.filter(email='norkans7@gmail.com'))
        self.assertFalse(Invitation.objects.get(pk=admin_invitation.pk).is_active)
        self.assertTrue(Invitation.objects.get(pk=viewer_invitation.pk).is_active)



class OrgBackgroundTest(DashTest):

    def setUp(self):
        super(OrgBackgroundTest, self).setUp()

        self.uganda = self.create_org('uganda', self.admin)
        self.nigeria = self.create_org('nigeria', self.admin)

    def test_org_background(self):
        create_url = reverse('orgs.orgbackground_create')

        response = self.client.get(create_url, SERVER_NAME='uganda.ureport.io')
        self.assertLoginRedirect(response)

        self.login(self.admin)
        response = self.client.get(create_url, SERVER_NAME='uganda.ureport.io')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(response.context['form'].fields), 4)
        self.assertTrue('org' not in response.context['form'].fields)

        upload = open("test-data/image.jpg", "r")

        post_data = dict(name="Orange Pattern", background_type="P", image=upload)
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME='uganda.ureport.io')
        self.assertEquals(response.status_code, 200)
        uganda_org_bg = OrgBackground.objects.order_by('-pk')[0]
        self.assertEquals(uganda_org_bg.org, self.uganda)
        self.assertEquals(uganda_org_bg.name, 'Orange Pattern')

        response = self.client.get(create_url, SERVER_NAME='nigeria.ureport.io')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(response.context['form'].fields), 4)
        self.assertTrue('org' not in response.context['form'].fields)

        upload = open("test-data/image.jpg", "r")

        post_data = dict(name="Orange Pattern", background_type="P", image=upload)
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME='nigeria.ureport.io')
        self.assertEquals(response.status_code, 200)
        nigeria_org_bg = OrgBackground.objects.order_by('-pk')[0]
        self.assertEquals(nigeria_org_bg.org, self.nigeria)
        self.assertEquals(nigeria_org_bg.name, 'Orange Pattern')

        list_url = reverse('orgs.orgbackground_list')

        response = self.client.get(list_url, SERVER_NAME='uganda.ureport.io')
        self.assertEquals(len(response.context['object_list']), 1)
        self.assertEquals(response.context['object_list'][0], uganda_org_bg)

        response = self.client.get(list_url, SERVER_NAME='nigeria.ureport.io')
        self.assertEquals(len(response.context['object_list']), 1)
        self.assertEquals(response.context['object_list'][0], nigeria_org_bg)

        uganda_bg_update_url = reverse('orgs.orgbackground_update', args=[uganda_org_bg.pk])
        nigeria_bg_update_url = reverse('orgs.orgbackground_update', args=[nigeria_org_bg.pk])

        response = self.client.get(uganda_bg_update_url, SERVER_NAME='nigeria.ureport.io')
        self.assertLoginRedirect(response)

        response = self.client.get(nigeria_bg_update_url, SERVER_NAME='uganda.ureport.io')
        self.assertLoginRedirect(response)

        response = self.client.get(uganda_bg_update_url, follow=True, SERVER_NAME='uganda.ureport.io')
        self.assertEquals(response.request['PATH_INFO'], uganda_bg_update_url)
        self.assertEquals(len(response.context['form'].fields), 5)
        self.assertTrue('org' not in response.context['form'].fields)

        upload = open("test-data/image.jpg", "r")
        post_data = dict(name="Orange Pattern Updated", background_type="P", image=upload)
        response = self.client.post(uganda_bg_update_url, post_data, follow=True, SERVER_NAME='uganda.ureport.io')
        self.assertEquals(response.request['PATH_INFO'], list_url)
        self.assertEquals(len(response.context['object_list']), 1)
        self.assertEquals(response.context['object_list'][0].name, "Orange Pattern Updated")

        self.login(self.superuser)
        response = self.client.get(create_url, SERVER_NAME='uganda.ureport.io')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(response.context['form'].fields), 5)
        self.assertTrue('org' in response.context['form'].fields)

        upload = open("test-data/image.jpg", "r")

        post_data = dict(name="Blue Pattern", background_type="P", image=upload)
        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME='uganda.ureport.io')
        self.assertTrue('form' in response.context)
        self.assertTrue('org' in response.context['form'].errors)

        upload = open("test-data/image.jpg", "r")

        post_data = dict(name="Blue Pattern", background_type="P", image=upload, org=self.uganda.pk)

        response = self.client.post(create_url, post_data, follow=True, SERVER_NAME='uganda.ureport.io')
        self.assertTrue('form' not in response.context)
        blue_bg = OrgBackground.objects.get(name="Blue Pattern")
        self.assertEquals(blue_bg.org, self.uganda)

        response = self.client.get(list_url, SERVER_NAME='uganda.ureport.io')
        self.assertEquals(len(response.context['object_list']), OrgBackground.objects.count())

        response = self.client.get(nigeria_bg_update_url, SERVER_NAME='nigeria.ureport.io')
        self.assertEquals(response.request['PATH_INFO'], nigeria_bg_update_url)
        self.assertEquals(len(response.context['form'].fields), 5)

        # clean up all uploaded images
        import os
        for org_bg in OrgBackground.objects.all():
            os.remove(org_bg.image.path)


class MockResponse(object):

    def __init__(self, status_code, content=''):
        self.content = content
        self.status_code = status_code

    def json(self, **kwargs):
        return json.loads(self.content)

class APITest(DashTest):
    def setUp(self):
        super(APITest, self).setUp()

        self.org = self.create_org("uganda", self.admin)
        self.org.api_token = 'UGANDA_API_TOKEN'
        self.org.set_config('state_label', 'LGA')
        self.org.set_config('district_label', 'Province')

        self.api = API(self.org)

    @patch('requests.models.Response', MockResponse)
    def test_get_group(self):
        with patch('requests.get') as mock_request_get:
            mock_request_get.return_value = MockResponse(200, json.dumps(dict(results=["GROUP_DICT"])))

            self.assertEquals(self.api.get_group('group_name'), "GROUP_DICT")
            mock_request_get.assert_called_once_with('%s/api/v1/groups.json' % settings.API_ENDPOINT,
                                                     params={'name': 'group_name'},
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})


        with patch('requests.get') as mock_request_get:
            mock_request_get.return_value = MockResponse(200, json.dumps(dict(results=[])))

            self.assertIsNone(self.api.get_group('group_name'))
            mock_request_get.assert_called_once_with('%s/api/v1/groups.json' % settings.API_ENDPOINT,
                                                     params={'name': 'group_name'},
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})


        with patch('requests.get') as mock_request_get:
            mock_request_get.return_value = MockResponse(200, json.dumps(dict(no_results_key="")))

            self.assertIsNone(self.api.get_group('group_name'))
            mock_request_get.assert_called_once_with('%s/api/v1/groups.json' % settings.API_ENDPOINT,
                                                     params={'name': 'group_name'},
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})




        with patch('requests.get') as mock_request_get:
            mock_request_get.return_value = MockResponse(404, json.dumps(dict(error="Not Found")))

            self.assertIsNone(self.api.get_group('group_name'))
            mock_request_get.assert_called_once_with('%s/api/v1/groups.json' % settings.API_ENDPOINT,
                                                     params={'name': 'group_name'},
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})


    @patch('requests.models.Response', MockResponse)
    def test_get_ruleset_results(self):
        with patch('requests.get') as mock_request_get:
            mock_request_get.return_value = MockResponse(200, json.dumps(dict(no_results_key="")))

            self.assertIsNone(self.api.get_ruleset_results(101))
            mock_request_get.assert_called_once_with('%s/api/v1/results.json?ruleset=101&segment=null' % settings.API_ENDPOINT,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertIsNone(self.api.get_ruleset_results(101, dict(location='State')))
            mock_request_get.assert_called_with('%s/api/v1/results.json?ruleset=101&segment=%s' % (settings.API_ENDPOINT, urllib.quote(unicode(json.dumps(dict(location='LGA'))).encode('utf8'))) ,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertIsNone(self.api.get_ruleset_results(101, dict(location='District')))
            mock_request_get.assert_called_with('%s/api/v1/results.json?ruleset=101&segment=%s' % (settings.API_ENDPOINT, urllib.quote(unicode(json.dumps(dict(location='Province'))).encode('utf8'))) ,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})
            self.assertEquals(mock_request_get.call_count, 3)

        with patch('requests.get') as mock_request_get:
            mock_request_get.return_value = MockResponse(404, json.dumps(dict(error="Not Found")))

            self.assertIsNone(self.api.get_ruleset_results(101))
            mock_request_get.assert_called_once_with('%s/api/v1/results.json?ruleset=101&segment=null' % settings.API_ENDPOINT,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertIsNone(self.api.get_ruleset_results(101, dict(location='State')))
            mock_request_get.assert_called_with('%s/api/v1/results.json?ruleset=101&segment=%s' % (settings.API_ENDPOINT, urllib.quote(unicode(json.dumps(dict(location='LGA'))).encode('utf8'))) ,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertIsNone(self.api.get_ruleset_results(101, dict(location='District')))
            mock_request_get.assert_called_with('%s/api/v1/results.json?ruleset=101&segment=%s' % (settings.API_ENDPOINT, urllib.quote(unicode(json.dumps(dict(location='Province'))).encode('utf8'))) ,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(mock_request_get.call_count, 3)

        with patch('requests.get') as mock_request_get:
            mock_request_get.return_value = MockResponse(200, json.dumps(dict(results=["RULESET_DATA"])))

            self.assertEquals(self.api.get_ruleset_results(101), ["RULESET_DATA"])
            mock_request_get.assert_called_once_with('%s/api/v1/results.json?ruleset=101&segment=null' % settings.API_ENDPOINT,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(self.api.get_ruleset_results(101, dict(location='State')), ["RULESET_DATA"])
            mock_request_get.assert_called_with('%s/api/v1/results.json?ruleset=101&segment=%s' % (settings.API_ENDPOINT, urllib.quote(unicode(json.dumps(dict(location='LGA'))).encode('utf8'))) ,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(self.api.get_ruleset_results(101, dict(location='District')), ["RULESET_DATA"])
            mock_request_get.assert_called_with('%s/api/v1/results.json?ruleset=101&segment=%s' % (settings.API_ENDPOINT, urllib.quote(unicode(json.dumps(dict(location='Province'))).encode('utf8'))) ,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(mock_request_get.call_count, 3)

    @patch('requests.models.Response', MockResponse)
    def test_get_contact_field_results(self):
        with patch('requests.get') as mock_request_get:
            mock_request_get.return_value = MockResponse(200, json.dumps(dict(results=["CONTACT_FIELD_DATA"])))

            self.assertEquals(self.api.get_contact_field_results('contact_field_name'), ["CONTACT_FIELD_DATA"])
            mock_request_get.assert_called_once_with('%s/api/v1/results.json?contact_field=contact_field_name&segment=null' % settings.API_ENDPOINT,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(self.api.get_contact_field_results('contact_field_name', dict(location='State')), ["CONTACT_FIELD_DATA"])
            mock_request_get.assert_called_with('%s/api/v1/results.json?contact_field=contact_field_name&segment=%s' % (settings.API_ENDPOINT, urllib.quote(unicode(json.dumps(dict(location='LGA'))).encode('utf8'))),
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(self.api.get_contact_field_results('contact_field_name', dict(location='District')), ["CONTACT_FIELD_DATA"])
            mock_request_get.assert_called_with('%s/api/v1/results.json?contact_field=contact_field_name&segment=%s' % (settings.API_ENDPOINT, urllib.quote(unicode(json.dumps(dict(location='Province'))).encode('utf8'))),
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(mock_request_get.call_count, 3)

        with patch('requests.get') as mock_request_get:
            mock_request_get.return_value = MockResponse(200, json.dumps(dict(no_results_key=["CONTACT_FIELD_DATA"])))

            self.assertIsNone(self.api.get_contact_field_results('contact_field_name'))
            mock_request_get.assert_called_once_with('%s/api/v1/results.json?contact_field=contact_field_name&segment=null' % settings.API_ENDPOINT,
                                                     headers={'Content-type': 'application/json',
                                                              'Accept': 'application/json',
                                                              'Authorization': 'Token %s' % self.org.api_token})

    @patch('requests.models.Response', MockResponse)
    def test_get_flows(self):
        with patch('requests.get') as mock_request_get:
            mock_request_get.side_effect = [MockResponse(200,
                                                         self.read_json('flows_page_1')
                                                         ),

                                            MockResponse(200,
                                                         self.read_json('flows_page_2')
                                                         )
                                            ]

            self.assertEquals(self.api.get_flows(), [dict(name="FLOW_1",
                                                          rulesets=["FLOW_1_RULESET_DICT"]),
                                                     dict(name="FLOW_3",
                                                          rulesets=["FLOW_3_RULESET_DICT"]),
                                                     dict(name="FLOW_5",
                                                          rulesets=["FLOW_5_RULESET_DICT"]),
                                                     dict(name="FLOW_6",
                                                          rulesets=["FLOW_6_RULESET_DICT"])
                                                     ])

            mock_request_get.assert_any_call('%s/api/v1/flows.json' % settings.API_ENDPOINT,
                                             headers={'Content-type': 'application/json',
                                                       'Accept': 'application/json',
                                                       'Authorization': 'Token %s' % self.org.api_token})

            mock_request_get.assert_any_call('NEXT_PAGE',
                                             headers={'Content-type': 'application/json',
                                                       'Accept': 'application/json',
                                                       'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(mock_request_get.call_count, 2)

        with patch('requests.get') as mock_request_get:
            mock_request_get.side_effect = [MockResponse(200,
                                                         self.read_json('flows_missing_next_key')
                                                         ),

                                            MockResponse(200,
                                                         self.read_json('flows_page_2')
                                                         )
                                            ]

            self.assertEquals(self.api.get_flows(), [dict(name="FLOW_1",
                                                          rulesets=["FLOW_1_RULESET_DICT"]),
                                                     dict(name="FLOW_3",
                                                          rulesets=["FLOW_3_RULESET_DICT"])])

            mock_request_get.assert_called_once_with('%s/api/v1/flows.json' % settings.API_ENDPOINT,
                                                      headers={'Content-type': 'application/json',
                                                               'Accept': 'application/json',
                                                               'Authorization': 'Token %s' % self.org.api_token})


    @patch('requests.models.Response', MockResponse)
    def test_get_flow(self):
        with patch('requests.get') as mock_request_get:
            mock_request_get.side_effect = [MockResponse(200,
                                                         self.read_json('flows_page_1')
                                                         ),

                                            MockResponse(200,
                                                         self.read_json('flows_page_2')
                                                         )
                                            ]

            self.assertEquals(self.api.get_flow(5), dict(name="FLOW_1", rulesets=['FLOW_1_RULESET_DICT']))

            mock_request_get.assert_any_call('%s/api/v1/flows.json?flow=5' % settings.API_ENDPOINT,
                                             headers={'Content-type': 'application/json',
                                                       'Accept': 'application/json',
                                                       'Authorization': 'Token %s' % self.org.api_token})

            mock_request_get.assert_any_call('NEXT_PAGE',
                                             headers={'Content-type': 'application/json',
                                                       'Accept': 'application/json',
                                                       'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(mock_request_get.call_count, 2)


        with patch('requests.get') as mock_request_get:
            mock_request_get.side_effect = [MockResponse(404,
                                                         self.read_json('flows_page_1')
                                                         ),

                                            MockResponse(404,
                                                         self.read_json('flows_page_2')
                                                         )
                                            ]

            self.assertIsNone(self.api.get_flow(5))

            mock_request_get.assert_any_call('%s/api/v1/flows.json?flow=5' % settings.API_ENDPOINT,
                                             headers={'Content-type': 'application/json',
                                                       'Accept': 'application/json',
                                                       'Authorization': 'Token %s' % self.org.api_token})

            mock_request_get.assert_any_call('NEXT_PAGE',
                                             headers={'Content-type': 'application/json',
                                                       'Accept': 'application/json',
                                                       'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(mock_request_get.call_count, 2)

        with patch('requests.get') as mock_request_get:
            mock_request_get.side_effect = [MockResponse(404,
                                                         self.read_json('flows_page_1')
                                                         ),

                                            MockResponse(200,
                                                         self.read_json('flows_page_2')
                                                         )
                                            ]

            self.assertEquals(self.api.get_flow(5), dict(name="FLOW_5", rulesets=['FLOW_5_RULESET_DICT']))

            mock_request_get.assert_any_call('%s/api/v1/flows.json?flow=5' % settings.API_ENDPOINT,
                                                      headers={'Content-type': 'application/json',
                                                               'Accept': 'application/json',
                                                               'Authorization': 'Token %s' % self.org.api_token})

            mock_request_get.assert_any_call('NEXT_PAGE',
                                             headers={'Content-type': 'application/json',
                                                       'Accept': 'application/json',
                                                       'Authorization': 'Token %s' % self.org.api_token})

            self.assertEquals(mock_request_get.call_count, 2)

    @patch('requests.models.Response', MockResponse)
    def test_build_boundaries(self):
        with patch('requests.get') as mock_request_get:
            mock_request_get.side_effect = [MockResponse(200,
                                                         self.read_json('boundaries_page_1')
                                                         ),
                                            MockResponse(200,
                                                         self.read_json('boundaries_page_2')
                                                         )]

            boundary_cached = dict()
            boundary_cached['geojson:%d' % self.org.id] = dict(type='FeatureCollection',
                                                               features=[dict(type='Feature',
                                                                              geometry="B_GEOMETRY_DICT_2",
                                                                              properties=dict(name="B_NAME_2",
                                                                                              id="B_BOUNDARY_2",
                                                                                              level=1)),
                                                                         dict(type='Feature',
                                                                              geometry="B_GEOMETRY_DICT_3",
                                                                              properties=dict(name="B_NAME_3",
                                                                                              id="B_BOUNDARY_3",
                                                                                              level=1))])
            boundary_cached['geojson:%d:B_BOUNDARY_2' % self.org.id] = dict(type='FeatureCollection',
                                                                            features=[dict(type='Feature',
                                                                                           geometry="B_GEOMETRY_DICT_4",
                                                                                           properties=dict(name="B_NAME_4",
                                                                                                           id="B_BOUNDARY_4",
                                                                                                           level=2))])

            self.assertEquals(self.api.build_boundaries(), boundary_cached)


        with patch('requests.get') as mock_request_get:
            mock_request_get.side_effect = [MockResponse(200,
                                                         self.read_json('boundaries_missing_next_key')
                                                         ),
                                            MockResponse(200,
                                                         self.read_json('boundaries_page_2')
                                                         )]

            boundary_cached = dict()
            boundary_cached['geojson:%d' % self.org.id] = dict(type='FeatureCollection',
                                                               features=[dict(type='Feature',
                                                                              geometry="B_GEOMETRY_DICT_2",
                                                                              properties=dict(name="B_NAME_2",
                                                                                              id="B_BOUNDARY_2",
                                                                                              level=1))
                                                                         ])

            self.assertEquals(self.api.build_boundaries(), boundary_cached)


        with patch('requests.get') as mock_request_get:
            mock_request_get.side_effect = [MockResponse(200,
                                                         self.read_json('boundaries_page_1')
                                                         ),
                                            MockResponse(200,
                                                         self.read_json('boundaries_page_2')
                                                         )]

            boundary_cached = dict()
            boundary_cached['geojson:%d' % self.org.id] = dict(type='FeatureCollection',
                                                               features=[dict(type='Feature',
                                                                              geometry="B_GEOMETRY_DICT_2",
                                                                              properties=dict(name="B_NAME_2",
                                                                                              id="B_BOUNDARY_2",
                                                                                              level=1)),
                                                                         dict(type='Feature',
                                                                              geometry="B_GEOMETRY_DICT_3",
                                                                              properties=dict(name="B_NAME_3",
                                                                                              id="B_BOUNDARY_3",
                                                                                              level=1))])
            boundary_cached['geojson:%d:B_BOUNDARY_2' % self.org.id] = dict(type='FeatureCollection',
                                                                            features=[dict(type='Feature',
                                                                                           geometry="B_GEOMETRY_DICT_4",
                                                                                           properties=dict(name="B_NAME_4",
                                                                                                           id="B_BOUNDARY_4",
                                                                                                           level=2))])

            self.assertEquals(self.api.get_country_geojson(), boundary_cached['geojson:%d' % self.org.id])

        with patch('requests.get') as mock_request_get:
            mock_request_get.side_effect = [MockResponse(200,
                                                         self.read_json('boundaries_page_1')
                                                         ),
                                            MockResponse(200,
                                                         self.read_json('boundaries_page_2')
                                                         )]

            boundary_cached = dict()
            boundary_cached['geojson:%d' % self.org.id] = dict(type='FeatureCollection',
                                                               features=[dict(type='Feature',
                                                                              geometry="B_GEOMETRY_DICT_2",
                                                                              properties=dict(name="B_NAME_2",
                                                                                              id="B_BOUNDARY_2",
                                                                                              level=1)),
                                                                         dict(type='Feature',
                                                                              geometry="B_GEOMETRY_DICT_3",
                                                                              properties=dict(name="B_NAME_3",
                                                                                              id="B_BOUNDARY_3",
                                                                                              level=1))])
            boundary_cached['geojson:%d:B_BOUNDARY_2' % self.org.id] = dict(type='FeatureCollection',
                                                                            features=[dict(type='Feature',
                                                                                           geometry="B_GEOMETRY_DICT_4",
                                                                                           properties=dict(name="B_NAME_4",
                                                                                                           id="B_BOUNDARY_4",
                                                                                                           level=2))])

            self.assertEquals(self.api.get_state_geojson('B_BOUNDARY_2'), boundary_cached['geojson:%d:B_BOUNDARY_2' % self.org.id])