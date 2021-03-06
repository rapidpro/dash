# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2016-10-26 15:13


import timezone_field.fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("orgs", "0016_taskstate_is_disabled")]

    operations = [
        migrations.AlterField(
            model_name="org",
            name="timezone",
            field=timezone_field.fields.TimeZoneField(
                default="UTC", help_text="The timezone your organization is in.", verbose_name="Timezone"
            ),
        )
    ]
