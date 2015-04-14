# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0009_auto_20150331_1452'),
    ]

    operations = [
        migrations.AddField(
            model_name='org',
            name='flag',
            field=models.ImageField(help_text='The flag logo that should be used for this organization on the landing page', null=True, upload_to='flags', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='org',
            name='language',
            field=models.CharField(choices=[(b'en', b'English'), (b'fr', b'French')], max_length=64, blank=True, help_text='The main language used by this organization', null=True, verbose_name='Language'),
            preserve_default=True,
        ),
    ]
