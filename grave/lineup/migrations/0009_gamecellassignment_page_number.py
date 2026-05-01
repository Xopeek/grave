from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lineup', '0008_schedulegame_game_map'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamecellassignment',
            name='page_number',
            field=models.PositiveSmallIntegerField(
                choices=[(1, 'Страница 1'), (2, 'Страница 2')],
                default=1,
                verbose_name='Номер страницы',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='gamecellassignment',
            name='unique_player_per_game',
        ),
        migrations.RemoveConstraint(
            model_name='gamecellassignment',
            name='unique_cell_per_game',
        ),
        migrations.AddConstraint(
            model_name='gamecellassignment',
            constraint=models.UniqueConstraint(
                fields=('game', 'participant', 'page_number'),
                name='unique_player_per_game',
            ),
        ),
        migrations.AddConstraint(
            model_name='gamecellassignment',
            constraint=models.UniqueConstraint(
                fields=('game', 'cell_index', 'page_number'),
                name='unique_cell_per_game',
            ),
        ),
    ]
