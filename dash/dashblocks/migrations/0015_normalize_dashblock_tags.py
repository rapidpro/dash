from django.db import migrations


def normalize_tags(apps, schema_editor):  # pragma: no cover
    """
    Normalizes existing tags to be lowercased, whitespace collapsed and space padded, e.g. " tag1 tag2 "
    """
    DashBlock = apps.get_model("dashblocks", "DashBlock")

    for block in DashBlock.objects.exclude(tags=None).exclude(tags="").iterator():
        if not block.tags.strip():
            continue

        normalized = " " + " ".join(block.tags.lower().split()) + " "
        if normalized != block.tags:
            block.tags = normalized
            block.save(update_fields=("tags",))


class Migration(migrations.Migration):
    dependencies = [
        ("dashblocks", "0014_alter_dashblockimage_image"),
    ]

    operations = [
        migrations.RunPython(normalize_tags, migrations.RunPython.noop),
    ]
