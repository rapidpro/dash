# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("orgs", "0006_auto_20140919_2056")]

    operations = [
        migrations.AlterField(
            model_name="invitation",
            name="created_by",
            field=models.ForeignKey(
                related_name="orgs_invitation_creations",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which originally created this item",
            ),
        ),
        migrations.AlterField(
            model_name="invitation",
            name="modified_by",
            field=models.ForeignKey(
                related_name="orgs_invitation_modifications",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which last modified this item",
            ),
        ),
        migrations.AlterField(
            model_name="invitation",
            name="org",
            field=models.ForeignKey(
                related_name="invitations",
                verbose_name="Org",
                on_delete=models.PROTECT,
                to="orgs.Org",
                help_text="The organization to which the account is invited to view",
            ),
        ),
        migrations.AlterField(
            model_name="org",
            name="administrators",
            field=models.ManyToManyField(
                help_text="The administrators in your organization",
                related_name="org_admins",
                verbose_name="Administrators",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="org",
            name="created_by",
            field=models.ForeignKey(
                related_name="orgs_org_creations",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which originally created this item",
            ),
        ),
        migrations.AlterField(
            model_name="org",
            name="editors",
            field=models.ManyToManyField(
                help_text="The editors in your organization",
                related_name="org_editors",
                verbose_name="Editors",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="org",
            name="modified_by",
            field=models.ForeignKey(
                related_name="orgs_org_modifications",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which last modified this item",
            ),
        ),
        migrations.AlterField(
            model_name="org",
            name="viewers",
            field=models.ManyToManyField(
                help_text="The viewers in your organization",
                related_name="org_viewers",
                verbose_name="Viewers",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="orgbackground",
            name="created_by",
            field=models.ForeignKey(
                related_name="orgs_orgbackground_creations",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which originally created this item",
            ),
        ),
        migrations.AlterField(
            model_name="orgbackground",
            name="modified_by",
            field=models.ForeignKey(
                related_name="orgs_orgbackground_modifications",
                to=settings.AUTH_USER_MODEL,
                on_delete=models.PROTECT,
                help_text="The user which last modified this item",
            ),
        ),
        migrations.AlterField(
            model_name="orgbackground",
            name="org",
            field=models.ForeignKey(
                related_name="backgrounds",
                verbose_name="Org",
                on_delete=models.PROTECT,
                to="orgs.Org",
                help_text="The organization in which the image will be used",
            ),
        ),
    ]
