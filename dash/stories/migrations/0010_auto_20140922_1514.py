# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0009_remove_story_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='story',
            name='created_by',
            field=models.ForeignKey(related_name='stories_story_creations', to=settings.AUTH_USER_MODEL, help_text='The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='story',
            name='modified_by',
            field=models.ForeignKey(related_name='stories_story_modifications', to=settings.AUTH_USER_MODEL, help_text='The user which last modified this item'),
        ),
        migrations.AlterField(
            model_name='story',
            name='video_id',
            field=models.CharField(help_text='The id of the YouTube video that should be linked to this story (this is the text that comes afer v= and before & in the YouTube URL)', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='storyimage',
            name='created_by',
            field=models.ForeignKey(related_name='stories_storyimage_creations', to=settings.AUTH_USER_MODEL, help_text='The user which originally created this item'),
        ),
        migrations.AlterField(
            model_name='storyimage',
            name='modified_by',
            field=models.ForeignKey(related_name='stories_storyimage_modifications', to=settings.AUTH_USER_MODEL, help_text='The user which last modified this item'),
        ),
        migrations.AlterField(
            model_name='storyimage',
            name='story',
            field=models.ForeignKey(related_name='images', to='stories.Story', help_text='The story to associate to'),
        ),
    ]
