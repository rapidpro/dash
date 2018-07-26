# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("orgs", "0012_auto_20150715_1816")]

    operations = [
        migrations.AlterField(
            model_name="org",
            name="language",
            field=models.CharField(
                help_text="The main language used by this organization",
                max_length=64,
                null=True,
                verbose_name="Language",
                blank=True,
            ),
        )
    ]
