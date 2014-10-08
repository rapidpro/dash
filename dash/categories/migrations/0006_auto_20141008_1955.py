# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0005_auto_20140922_1514'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='org',
            field=models.ForeignKey(related_name='categories', to='orgs.Org', help_text='The organization this category applies to'),
        ),
    ]
