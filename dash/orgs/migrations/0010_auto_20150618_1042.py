# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0009_auto_20150331_1452'),
    ]

    operations = [
        migrations.AlterField(
            model_name='org',
            name='subdomain',
            field=models.SlugField(null=True, error_messages={'unique': 'This subdomain is not available'}, max_length=255, blank=True, help_text='The subdomain for this U-Report instance', unique=True, verbose_name='Subdomain'),
            preserve_default=True,
        ),
    ]
