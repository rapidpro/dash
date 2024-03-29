# Generated by Django 3.2.6 on 2021-09-10 14:50

import functools

from django.db import migrations, models

import dash.utils


class Migration(migrations.Migration):

    dependencies = [
        ("categories", "0008_alter_category_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="An optional image that can describe this category",
                null=True,
                upload_to=functools.partial(dash.utils.generate_file_path, *("categories",), **{}),
            ),
        ),
        migrations.AlterField(
            model_name="categoryimage",
            name="image",
            field=models.ImageField(
                help_text="The image file to use",
                upload_to=functools.partial(dash.utils.generate_file_path, *("categories",), **{}),
            ),
        ),
    ]
