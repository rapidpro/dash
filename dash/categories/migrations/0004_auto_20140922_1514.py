# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0003_auto_20140904_0927'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='created_by',
            field=models.ForeignKey(related_name=b'categories_category_creations', to=settings.AUTH_USER_MODEL, help_text=b'The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='category',
            name='modified_by',
            field=models.ForeignKey(related_name=b'categories_category_modifications', to=settings.AUTH_USER_MODEL, help_text=b'The user which last modified this item'),
        ),
        migrations.AlterField(
            model_name='categoryimage',
            name='category',
            field=models.ForeignKey(related_name=b'images', to='categories.Category', help_text='The category this image represents'),
        ),
        migrations.AlterField(
            model_name='categoryimage',
            name='created_by',
            field=models.ForeignKey(related_name=b'categories_categoryimage_creations', to=settings.AUTH_USER_MODEL, help_text=b'The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='categoryimage',
            name='modified_by',
            field=models.ForeignKey(related_name=b'categories_categoryimage_modifications', to=settings.AUTH_USER_MODEL, help_text=b'The user which last modified this item'),
        ),
    ]
