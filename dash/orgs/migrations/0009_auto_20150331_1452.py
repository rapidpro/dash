# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0008_org_timezone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='org',
            name='language',
            field=models.CharField(choices=[(b'en', b'English'), (b'fr', b'French'), (b'es', b'Spanish'), (b'ar', b'Arabic')], max_length=64, blank=True, help_text='The main language used by this organization', null=True, verbose_name='Language'),
            preserve_default=True,
        ),
    ]
