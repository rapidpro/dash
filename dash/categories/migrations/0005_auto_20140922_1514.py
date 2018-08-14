from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("categories", "0004_auto_20140904_0927")]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="created_by",
            field=models.ForeignKey(
                related_name="categories_category_creations",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which originally created this item",
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="modified_by",
            field=models.ForeignKey(
                related_name="categories_category_modifications",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which last modified this item",
            ),
        ),
        migrations.AlterField(
            model_name="categoryimage",
            name="category",
            field=models.ForeignKey(
                related_name="images",
                on_delete=models.PROTECT,
                to="categories.Category",
                help_text="The category this image represents",
            ),
        ),
        migrations.AlterField(
            model_name="categoryimage",
            name="created_by",
            field=models.ForeignKey(
                related_name="categories_categoryimage_creations",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which originally created this item",
            ),
        ),
        migrations.AlterField(
            model_name="categoryimage",
            name="modified_by",
            field=models.ForeignKey(
                related_name="categories_categoryimage_modifications",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which last modified this item",
            ),
        ),
    ]
