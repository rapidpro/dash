# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0015_auto_20160209_0926'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskstate',
            name='is_disabled',
            field=models.BooleanField(default=False),
        ),
    ]
