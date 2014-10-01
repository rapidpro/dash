# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0006_auto_20140919_2056'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invitation',
            name='created_by',
            field=models.ForeignKey(related_name=b'orgs_invitation_creations', to=settings.AUTH_USER_MODEL, help_text=b'The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='modified_by',
            field=models.ForeignKey(related_name=b'orgs_invitation_modifications', to=settings.AUTH_USER_MODEL, help_text=b'The user which last modified this item'),
        ),
        migrations.AlterField(
            model_name='invitation',
            name='org',
            field=models.ForeignKey(related_name=b'invitations', verbose_name='Org', to='orgs.Org', help_text='The organization to which the account is invited to view'),
        ),
        migrations.AlterField(
            model_name='org',
            name='administrators',
            field=models.ManyToManyField(help_text='The administrators in your organization', related_name=b'org_admins', verbose_name='Administrators', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='org',
            name='created_by',
            field=models.ForeignKey(related_name=b'orgs_org_creations', to=settings.AUTH_USER_MODEL, help_text=b'The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='org',
            name='editors',
            field=models.ManyToManyField(help_text='The editors in your organization', related_name=b'org_editors', verbose_name='Editors', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='org',
            name='modified_by',
            field=models.ForeignKey(related_name=b'orgs_org_modifications', to=settings.AUTH_USER_MODEL, help_text=b'The user which last modified this item'),
        ),
        migrations.AlterField(
            model_name='org',
            name='viewers',
            field=models.ManyToManyField(help_text='The viewers in your organization', related_name=b'org_viewers', verbose_name='Viewers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='orgbackground',
            name='created_by',
            field=models.ForeignKey(related_name=b'orgs_orgbackground_creations', to=settings.AUTH_USER_MODEL, help_text=b'The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='orgbackground',
            name='modified_by',
            field=models.ForeignKey(related_name=b'orgs_orgbackground_modifications', to=settings.AUTH_USER_MODEL, help_text=b'The user which last modified this item'),
        ),
        migrations.AlterField(
            model_name='orgbackground',
            name='org',
            field=models.ForeignKey(related_name=b'backgrounds', verbose_name='Org', to='orgs.Org', help_text='The organization in which the image will be used'),
        ),
    ]
