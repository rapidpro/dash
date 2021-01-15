from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='backend',
            field=models.CharField(default='rapidpro', max_length=16),
        ),
    ]
