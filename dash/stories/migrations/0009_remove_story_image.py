# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("stories", "0008_auto_20140912_0524")]

    operations = [migrations.RemoveField(model_name="story", name="image")]
