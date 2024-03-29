# Generated by Django 3.2.6 on 2021-10-26 18:01

import functools

from django.db import migrations, models

import dash.stories.models
import dash.utils


class Migration(migrations.Migration):

    dependencies = [
        ("stories", "0014_alter_storyimage_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="story",
            name="attachment",
            field=models.FileField(
                blank=True,
                help_text="The PDF report to attach",
                null=True,
                upload_to=functools.partial(dash.utils.generate_file_path, *("story_attachments",), **{}),
                validators=[dash.stories.models.validate_file_extension],
            ),
        ),
    ]
