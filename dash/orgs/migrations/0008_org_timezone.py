# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0007_auto_20140922_1514'),
    ]

    operations = [
        migrations.AddField(
            model_name='org',
            name='timezone',
            field=models.CharField(default='UTC', max_length=64, verbose_name='Timezone'),
            preserve_default=True,
        ),
    ]
