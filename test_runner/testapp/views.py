from smartmin.views import SmartCRUDL, SmartTemplateView

from test_runner.testapp.models import Contact


class ContactCRUDL(SmartCRUDL):
    model = Contact
    actions = ('test_tags', 'list')

    class TestTags(SmartTemplateView):
        permission = None
        template_name = 'tags_test.html'
