from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lineup', '0010_gamecellassignment_role_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamecellassignment',
            name='vehicle_icon',
            field=models.CharField(
                blank=True,
                default='',
                max_length=120,
                verbose_name='Техника',
            ),
        ),
    ]
