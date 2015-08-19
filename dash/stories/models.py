from __future__ import unicode_literals

from smartmin.models import SmartModel

from django.db import models
from django.utils.translation import ugettext_lazy as _

from dash.categories.models import Category
from dash.orgs.models import Org


class Story(SmartModel):
    title = models.CharField(
        max_length=255,
        help_text=_("The title for this story"))

    featured = models.BooleanField(
        default=False,
        help_text=_("Whether this story is featured"))
    summary = models.TextField(
        null=True, blank=True,
        help_text=_("The summary for the story"))

    content = models.TextField(help_text=_("The body of text for the story"))

    audio_link = models.URLField(max_length=255, blank=True, null=True,
                                 help_text=_("A link to an mp3 file to publish on this story"))

    video_id = models.CharField(
        blank=True, null=True, max_length=255,
        help_text=_("The id of the YouTube video that should be linked to "
                    "this story (this is the text that comes afer v= and "
                    "before & in the YouTube URL)"))

    tags = models.CharField(
        blank=True, null=True, max_length=255,
        help_text=_("Any tags for this story, separated by spaces, can be "
                    "used to do more advanced filtering, optional"))

    category = models.ForeignKey(
        Category, null=True, blank=True,
        help_text=_("The category for this story"))

    org = models.ForeignKey(
        Org,
        help_text=_("The organization this story belongs to"))

    @classmethod
    def format_audio_link(cls, link):
        formatted_link = link
        if not formatted_link.startswith('http://'):
            formatted_link = 'http://' + formatted_link
        return formatted_link


    @classmethod
    def space_tags(cls, tags):
        """
        If we have tags set, then adds spaces before and after to allow for SQL
        querying for them.
        """
        if tags and tags.strip():
            return " " + tags.strip().lower() + " "

    def teaser(self, field, length):
        if not field:
            return ""
        words = field.split(" ")

        if len(words) < length:
            return field
        else:
            return " ".join(words[:length]) + " .."

    def long_teaser(self):
        if self.summary:
            return self.teaser(self.summary, 100)
        return self.teaser(self.content, 100)

    def short_teaser(self):
        if self.summary:
            return self.teaser(self.summary, 40)
        return self.teaser(self.content, 40)

    def get_featured_images(self):
        return self.images.filter(is_active=True).exclude(image='')

    def get_category_image(self):
        cat_image = None
        if self.category and self.category.is_active:
            cat_image = self.category.get_first_image()

        if not cat_image:
            if self.get_featured_images():
                cat_image = self.get_featured_images()[0].image

        return cat_image

    def get_audio_link(self):
        if not self.audio_link:
            return None

        return str(self.audio_link)

    def get_image(self):
        cat_image = None
        if self.get_featured_images():
            cat_image = self.get_featured_images()[0].image

        if not cat_image:
            if self.category and self.category.is_active:
                cat_image = self.category.get_first_image()

        return cat_image

    class Meta:
        verbose_name_plural = _("Stories")


class StoryImage(SmartModel):
    name = models.CharField(max_length=64,
                            help_text=_("The name to describe this image"))

    story = models.ForeignKey(Story, related_name="images",
                              help_text=_("The story to associate to"))

    image = models.ImageField(upload_to='stories',
                              help_text=_("The image file to use"))
