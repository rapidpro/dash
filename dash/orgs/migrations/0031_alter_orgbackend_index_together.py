# Generated by Django 4.1.7 on 2023-03-29 13:57

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0030_alter_invitation_created_by_and_more"),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name="orgbackend",
            index_together={("org", "is_active", "slug")},
        ),
    ]
