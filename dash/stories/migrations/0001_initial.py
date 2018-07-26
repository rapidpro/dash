# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("orgs", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Story",
            fields=[
                ("id", models.AutoField(verbose_name="ID", serialize=False, auto_created=True, primary_key=True)),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, help_text="Whether this item is active, use this instead of deleting"
                    ),
                ),
                (
                    "created_on",
                    models.DateTimeField(help_text="When this item was originally created", auto_now_add=True),
                ),
                ("modified_on", models.DateTimeField(help_text="When this item was last modified", auto_now=True)),
                ("title", models.CharField(help_text="The title for this story", max_length=255)),
                ("featured", models.BooleanField(default=False, help_text="Whether this story is featured")),
                ("content", models.TextField(help_text="The body of text for the story")),
                (
                    "image",
                    models.ImageField(
                        help_text="Any image that should be displayed with this story", upload_to="stories"
                    ),
                ),
                (
                    "video_id",
                    models.CharField(
                        help_text="The id of the YouTube video that should be linked to this story",
                        max_length=255,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "tags",
                    models.CharField(
                        help_text="Any tags for this story, separated by spaces, can be used to do more advanced filtering, optional",
                        max_length=255,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        help_text="The user which originally created this item",
                        on_delete=models.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        help_text="The user which last modified this item",
                        on_delete=models.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "org",
                    models.ForeignKey(
                        help_text="The organization this story belongs to", on_delete=models.PROTECT, to="orgs.Org"
                    ),
                ),
            ],
            options={"verbose_name_plural": "Stories"},
            bases=(models.Model,),
        )
    ]
