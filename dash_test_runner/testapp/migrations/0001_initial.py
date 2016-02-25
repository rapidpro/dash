# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0015_auto_20160209_0926'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', models.CharField(unique=True, max_length=36)),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('is_active', models.BooleanField(default=True)),
                ('org', models.ForeignKey(to='orgs.Org')),
            ],
        ),
    ]
