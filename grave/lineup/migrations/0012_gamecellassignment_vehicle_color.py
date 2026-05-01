from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lineup', '0011_gamecellassignment_vehicle_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamecellassignment',
            name='vehicle_color',
            field=models.CharField(
                blank=True,
                default='#ffffff',
                max_length=7,
                verbose_name='Цвет техники',
            ),
        ),
    ]
