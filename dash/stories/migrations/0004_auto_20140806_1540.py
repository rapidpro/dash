# -*- coding: utf-8 -*-


from django.db import migrations


def populate_story_summary(apps, schema_editor):
    Story = apps.get_model("stories", "Story")
    for story in Story.objects.all():
        story.summary = story.content
        story.save()


class Migration(migrations.Migration):

    dependencies = [("stories", "0003_story_summary")]

    operations = [migrations.RunPython(populate_story_summary)]
