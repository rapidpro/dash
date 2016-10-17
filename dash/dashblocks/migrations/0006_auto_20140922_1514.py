# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('dashblocks', '0005_auto_20140904_0957'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dashblock',
            name='created_by',
            field=models.ForeignKey(related_name='dashblocks_dashblock_creations', to=settings.AUTH_USER_MODEL, help_text='The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='dashblock',
            name='modified_by',
            field=models.ForeignKey(related_name='dashblocks_dashblock_modifications', to=settings.AUTH_USER_MODEL, help_text='The user which last modified this item'),
        ),
        migrations.AlterField(
            model_name='dashblockimage',
            name='created_by',
            field=models.ForeignKey(related_name='dashblocks_dashblockimage_creations', to=settings.AUTH_USER_MODEL, help_text='The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='dashblockimage',
            name='dashblock',
            field=models.ForeignKey(related_name='images', to='dashblocks.DashBlock'),
        ),
        migrations.AlterField(
            model_name='dashblockimage',
            name='modified_by',
            field=models.ForeignKey(related_name='dashblocks_dashblockimage_modifications', to=settings.AUTH_USER_MODEL, help_text='The user which last modified this item'),
        ),
        migrations.AlterField(
            model_name='dashblocktype',
            name='created_by',
            field=models.ForeignKey(related_name='dashblocks_dashblocktype_creations', to=settings.AUTH_USER_MODEL, help_text='The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='dashblocktype',
            name='modified_by',
            field=models.ForeignKey(related_name='dashblocks_dashblocktype_modifications', to=settings.AUTH_USER_MODEL, help_text='The user which last modified this item'),
        ),
    ]
