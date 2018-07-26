from __future__ import unicode_literals

from dash_test_runner.testapp.models import Contact
from smartmin.views import SmartCRUDL, SmartTemplateView


class ContactCRUDL(SmartCRUDL):
    model = Contact
    actions = ('test_tags', 'list')

    class TestTags(SmartTemplateView):
        permission = None
        template_name = 'tags_test.html'
