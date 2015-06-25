from __future__ import unicode_literals
from django.db import models
from smartmin.models import SmartModel
from dash.orgs.models import Org
from django.utils.translation import ugettext_lazy as _


class Category(SmartModel):
    """
    Every organization can choose to categorize their polls or stories according to their needs.
    """
    name = models.CharField(max_length=64,
                            help_text=_("The name of this category"))

    image = models.ImageField(upload_to='categories', null=True, blank=True,
                              help_text=_("An optional image that can describe this category"))

    org = models.ForeignKey(Org, related_name='categories',
                            help_text=_("The organization this category applies to"))

    def get_first_image(self):
        cat_images = self.images.filter(is_active=True).exclude(image='')
        if cat_images and cat_images.first().image:
            return cat_images.first().image

    def __unicode__(self):
        return "%s - %s" % (self.org, self.name)

    class Meta:
        unique_together = ('name', 'org')
        verbose_name_plural = _("Categories")


class CategoryImage(SmartModel):
    name = models.CharField(max_length=64,
                            help_text=_("The name to describe this image"))

    category = models.ForeignKey(Category, related_name='images',
                                 help_text=_("The category this image represents"))

    image = models.ImageField(upload_to='categories',
                              help_text=_("The image file to use"))

    def __unicode__(self):
        return "%s - %s" % (self.category.name, self.name)
