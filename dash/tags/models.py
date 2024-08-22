from smartmin.models import SmartModel

from django.db import models
from django.utils.translation import gettext_lazy as _

from dash.orgs.models import Org


class Tag(SmartModel):

    name = models.CharField(max_length=64, help_text=_("The name of this tag"))
    org = models.ForeignKey(Org, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return self.name

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name", "org"], name="tags_tag_name_org_unique")]
