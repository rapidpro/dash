# Generated by Django 5.0.8 on 2024-08-22 08:59

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [
        ("tags", "0001_initial"),
        ("tags", "0002_alter_tag_created_by_alter_tag_modified_by"),
        ("tags", "0003_alter_tag_unique_together_and_more"),
    ]

    initial = True

    dependencies = [
        ("orgs", "0026_fix_org_config_rapidpro"),
        ("orgs", "0033_rename_orgs_orgbac_org_id_607508_idx_orgs_orgbac_org_slug_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, help_text="Whether this item is active, use this instead of deleting"
                    ),
                ),
                (
                    "created_on",
                    models.DateTimeField(
                        blank=True,
                        default=django.utils.timezone.now,
                        editable=False,
                        help_text="When this item was originally created",
                    ),
                ),
                (
                    "modified_on",
                    models.DateTimeField(
                        blank=True,
                        default=django.utils.timezone.now,
                        editable=False,
                        help_text="When this item was last modified",
                    ),
                ),
                ("name", models.CharField(help_text="The name of this tag", max_length=64)),
                (
                    "created_by",
                    models.ForeignKey(
                        help_text="The user which originally created this item",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_creations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        help_text="The user which last modified this item",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_modifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("org", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="orgs.org")),
            ],
            options={
                "unique_together": set(),
            },
        ),
        migrations.AddConstraint(
            model_name="tag",
            constraint=models.UniqueConstraint(fields=("name", "org"), name="tags_tag_name_org_unique"),
        ),
    ]
