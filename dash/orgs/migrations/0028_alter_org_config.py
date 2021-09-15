# Generated by Django 3.2.6 on 2021-09-15 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orgs", "0027_alter_org_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="org",
            name="config",
            field=models.JSONField(
                default=dict,
                help_text="JSON blob used to store configuration information associated with this organization",
            ),
        ),
    ]
