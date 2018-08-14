# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):
    def move_images(apps, schema_editor):
        # for each story we want to move any image currently on it and instead create a StoryImage for it
        Story = apps.get_model("stories", "Story")
        StoryImage = apps.get_model("stories", "StoryImage")

        for story in Story.objects.exclude(image=None):
            StoryImage.objects.create(
                story=story, image=story.image, created_by=story.created_by, modified_by=story.modified_by
            )

    dependencies = [("stories", "0007_storyimage")]

    operations = [migrations.RunPython(move_images)]
