from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lineup', '0009_gamecellassignment_page_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamecellassignment',
            name='role_icon',
            field=models.CharField(
                blank=True,
                default='',
                max_length=120,
                verbose_name='Роль',
            ),
        ),
    ]
