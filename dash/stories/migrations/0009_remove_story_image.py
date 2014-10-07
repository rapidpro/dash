# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0008_auto_20140912_0524'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='story',
            name='image',
        ),
    ]
