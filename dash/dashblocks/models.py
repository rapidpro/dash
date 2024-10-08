from functools import partial

from smartmin.models import SmartModel

from django.db import models
from django.utils.translation import gettext_lazy as _

from dash.orgs.models import Org
from dash.utils import generate_file_path


class DashBlockType(SmartModel):
    """
    Dash Block Types just group fields by a slug.. letting you do lookups by
    type. In the future it may be nice to specify which fields should be
    displayed when creating fields of a new type.
    """

    name = models.CharField(max_length=75, unique=True, help_text=_("The human readable name for this content type"))
    slug = models.SlugField(
        max_length=50,
        unique=True,
        help_text=_("The slug to idenfity this content type, used with the " "template tags"),
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text=_("A description of where this content type is used on the " "site and how it will be dsiplayed"),
    )

    has_title = models.BooleanField(default=True, help_text=_("Whether this content should include a title"))
    has_image = models.BooleanField(default=True, help_text=_("Whether this content should include an image"))
    has_rich_text = models.BooleanField(
        default=True, help_text=_("Whether this content should use a rich HTML editor")
    )
    has_summary = models.BooleanField(default=True, help_text=_("Whether this content should include a summary field"))
    has_link = models.BooleanField(default=True, help_text=_("Whether this content should include a link"))
    has_gallery = models.BooleanField(
        default=False, help_text=_("Whether this content should allow upload of additional " "images, ie a gallery")
    )
    has_color = models.BooleanField(default=False, help_text=_("Whether this content has a color field"))
    has_video = models.BooleanField(
        default=False, help_text=_("Whether this content should allow setting a YouTube id")
    )
    has_tags = models.BooleanField(default=False, help_text=_("Whether this content should allow tags"))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["slug", "name"], name="dashblocktype_slug_name_idx")]


class DashBlock(SmartModel):
    """
    A DashBlock is just a block of content, organized by type and priority.
    All fields are optional letting you use them for different things.
    """

    dashblock_type = models.ForeignKey(
        DashBlockType,
        on_delete=models.PROTECT,
        verbose_name=_("Content Type"),
        help_text=_("The category, or type for this content block"),
    )

    title = models.CharField(
        max_length=255, blank=True, null=True, help_text=_("The title for this block of content, optional")
    )
    summary = models.TextField(blank=True, null=True, help_text=_("The summary for this item, should be short"))
    content = models.TextField(blank=True, null=True, help_text=_("The body of text for this content block, optional"))
    image = models.ImageField(
        blank=True,
        null=True,
        upload_to=partial(generate_file_path, "dashblocks"),
        help_text=_("Any image that should be displayed with this content " "block, optional"),
    )
    color = models.CharField(
        blank=True,
        null=True,
        max_length=16,
        help_text=_("A background color to use for the image, in the " "format: #rrggbb"),
    )
    link = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text=_("Any link that should be associated with this content " "block, optional"),
    )
    video_id = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text=_("The id of the YouTube video that should be linked to " "this item"),
    )
    tags = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text=_(
            "Any tags for this content block, separated by spaces, "
            "can be used to do more advanced filtering, optional"
        ),
    )
    priority = models.IntegerField(
        default=0, help_text=_("The priority for this block, higher priority blocks " "come first")
    )

    org = models.ForeignKey(
        Org, on_delete=models.PROTECT, help_text=_("The organization this content block belongs to")
    )

    def teaser(self, field, length):
        words = field.split(" ")

        if len(words) < length:
            return field
        else:
            return " ".join(words[:length]) + " ..."

    def long_content_teaser(self):
        return self.teaser(self.content, 100)

    def short_content_teaser(self):
        return self.teaser(self.content, 40)

    def long_summary_teaser(self):
        return self.teaser(self.summary, 100)

    def short_summary_teaser(self):
        return self.teaser(self.summary, 40)

    def space_tags(self):
        """
        If we have tags set, then adds spaces before and after to allow for SQL
        querying for them.
        """
        if self.tags and self.tags.strip():
            self.tags = " " + self.tags.strip().lower() + " "

    def sorted_images(self):
        return self.images.filter(is_active=True).order_by("-priority")

    def __str__(self):
        if self.dashblock_type.has_title:
            return self.title
        return "%s - %d" % (self.dashblock_type, self.pk)

    class Meta:
        ordering = ["dashblock_type", "title"]
        indexes = [
            models.Index(fields=["org", "is_active", "dashblock_type", "priority"], name="dashblock_org_typ_prio_idx")
        ]


class DashBlockImage(SmartModel):
    dashblock = models.ForeignKey(DashBlock, on_delete=models.PROTECT, related_name="images")
    image = models.ImageField(
        upload_to=partial(generate_file_path, "dashblock_images/"), width_field="width", height_field="height"
    )
    caption = models.CharField(max_length=64)
    priority = models.IntegerField(default=0, blank=True, null=True)
    width = models.IntegerField()
    height = models.IntegerField()

    def __str__(self):
        return self.image.url
