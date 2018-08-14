# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("orgs", "0011_auto_20150710_1612")]

    operations = [
        migrations.AlterField(
            model_name="invitation",
            name="email",
            field=models.EmailField(
                help_text="The email to which we send the invitation of the viewer",
                max_length=254,
                verbose_name="Email",
            ),
        )
    ]
