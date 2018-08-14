from smartmin.models import SmartModel

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from dash.orgs.models import Org


@python_2_unicode_compatible
class Category(SmartModel):
    """
    Every organization can choose to categorize their polls or stories
    according to their needs.
    """

    name = models.CharField(max_length=64, help_text=_("The name of this category"))

    image = models.ImageField(
        upload_to="categories", null=True, blank=True, help_text=_("An optional image that can describe this category")
    )

    org = models.ForeignKey(
        Org,
        on_delete=models.PROTECT,
        related_name="categories",
        help_text=_("The organization this category applies to"),
    )

    def get_first_image(self):
        cat_images = self.images.filter(is_active=True).exclude(image="")
        if cat_images and cat_images.first().image:
            return cat_images.first().image

    def get_label_from_instance(self):
        label = str(self)
        if isinstance(label, bytes):
            label = label.decode("utf-8")

        if not self.is_active:
            label = "%s %s" % (label, "(Inactive)")
        return label

    def __str__(self):
        return "%s - %s" % (self.org, self.name)

    class Meta:
        unique_together = ("name", "org")
        verbose_name_plural = _("Categories")


@python_2_unicode_compatible
class CategoryImage(SmartModel):
    name = models.CharField(max_length=64, help_text=_("The name to describe this image"))

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="images", help_text=_("The category this image represents")
    )

    image = models.ImageField(upload_to="categories", help_text=_("The image file to use"))

    def __str__(self):
        return "%s - %s" % (self.category.name, self.name)
