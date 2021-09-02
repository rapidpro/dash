from smartmin.views import SmartCreateView, SmartCRUDL, SmartDeleteView, SmartListView, SmartUpdateView

from django.db.models.functions import Lower
from django.utils.translation import ugettext_lazy as _

from dash.orgs.views import OrgObjPermsMixin, OrgPermsMixin
from dash.tags.models import Tag


class TagCRUDL(SmartCRUDL):
    model = Tag
    actions = ("create", "list", "update", "delete")

    class Create(OrgPermsMixin, SmartCreateView):
        fields = ("name",)

        def pre_save(self, obj):
            obj = super(TagCRUDL.Create, self).pre_save(obj)

            org = self.derive_org()
            obj.org = org

            return obj

    class Update(OrgObjPermsMixin, SmartUpdateView):
        fields = ("name",)
        delete_url = "id@tags.tag_delete"

    class List(OrgPermsMixin, SmartListView):
        fields = ("name", "modified_on", "created_on")

        def get_queryset(self, **kwargs):
            queryset = super(TagCRUDL.List, self).get_queryset(**kwargs)
            queryset = queryset.filter(org=self.derive_org()).order_by(Lower("name"))

            return queryset

    class Delete(OrgObjPermsMixin, SmartDeleteView):
        cancel_url = "id@tags.tag_update"
        redirect_url = "@tags.tag_list"
        default_template = "smartmin/delete_confirm.html"
        submit_button_name = _("Delete")
