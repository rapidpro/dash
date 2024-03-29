# Generated by Django 3.2.6 on 2021-09-10 14:50

import functools

from django.db import migrations, models

import dash.utils


class Migration(migrations.Migration):

    dependencies = [
        ("stories", "0013_auto_20170301_0914"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storyimage",
            name="image",
            field=models.ImageField(
                help_text="The image file to use",
                upload_to=functools.partial(dash.utils.generate_file_path, *("stories",), **{}),
            ),
        ),
    ]
