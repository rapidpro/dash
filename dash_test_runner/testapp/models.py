from __future__ import unicode_literals


from dash.orgs.models import Org
from dash.utils.sync import BaseSyncer
from django.db import models
from django.utils.translation import ugettext as _
from django_redis import get_redis_connection


class Contact(models.Model):
    org = models.ForeignKey(Org)

    uuid = models.CharField(max_length=36, unique=True)

    name = models.CharField(verbose_name=_("Name"), max_length=128)

    is_active = models.BooleanField(default=True)

    @classmethod
    def lock(cls, org, uuid):
        return get_redis_connection().lock('contact-lock:%d:%s' % (org.pk, uuid), timeout=60)


class ContactSyncer(BaseSyncer):
    model = Contact

    def local_kwargs(self, org, remote):
        if remote.blocked:  # we don't store blocked contacts
            return None

        return {
            'org': org,
            'uuid': remote.uuid,
            'name': remote.name
        }

    def update_required(self, local, remote, remote_as_kwargs):
        return local.name != remote.name
