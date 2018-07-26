# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("stories", "0011_story_audio_link")]

    operations = [
        migrations.AddField(
            model_name="story",
            name="written_by",
            field=models.CharField(help_text="The writer of the story", max_length=255, null=True, blank=True),
        )
    ]
