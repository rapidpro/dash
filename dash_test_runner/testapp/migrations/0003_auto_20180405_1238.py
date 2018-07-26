import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0002_auto_20180312_1302'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='backend',
            field=models.ForeignKey(on_delete=models.PROTECT, to='orgs.OrgBackend'),
        ),
    ]
