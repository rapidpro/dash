# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-12 13:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='backend',
            field=models.CharField(default='rapidpro', max_length=16),
        ),
        migrations.AlterField(
            model_name='contact',
            name='uuid',
            field=models.CharField(max_length=36),
        ),
    ]
