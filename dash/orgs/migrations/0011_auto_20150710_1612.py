# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0010_auto_20150618_1042'),
    ]

    operations = [
        migrations.AddField(
            model_name='org',
            name='domain',
            field=models.CharField(null=True, error_messages={'unique': 'This domain is not available'}, max_length=255, blank=True, help_text='The custom domain for this U-Report instance', unique=True, verbose_name='Domain'),
            preserve_default=True,
        ),
    ]
