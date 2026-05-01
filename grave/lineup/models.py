from django.db.models import Model
from django.db import models


class DiscordChannel(Model):
    name = models.TextField(
        'Название',
        max_length=100
    )
    guild_id = models.BigIntegerField(
        'ID Discord Channel',
    )
    channel_id = models.BigIntegerField(
        'ID Discord Forum',
    )

    class Meta:
        verbose_name = 'Discord Channel'
        verbose_name_plural = 'Discord Channels'
        ordering = ('name',)

    def __str__(self):
        return self.name


class ScheduleGame(Model):
    FORMAT_CHOICES = [
        ('20x20', '20x20'),
        ('26x26', '26x26'),
        ('30x30', '30x30'),
        ('48x48', '48x48'),
    ]
    discord_thread_id = models.BigIntegerField(
        'ID треда',
        unique=True
    )
    name = models.TextField(
        'Название',
    )
    archived = models.BooleanField(
        'Архив',
        default=False
    )
    tags = models.TextField(
        'Тэги',
        blank=True,
    )
    game_format = models.CharField(
        'Формат',
        max_length=10,
        choices=FORMAT_CHOICES,
        default='20x20'
    )
    game_map = models.CharField(
        'Карта',
        max_length=255,
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(
        'Дата создания'
    )

    class Meta:
        verbose_name = 'Расписание игр'
        verbose_name_plural = 'Расписание игр'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name


class GameParticipant(Model):
    STATUS_CHOICES = [
        ('accepted', 'Accepted'),
        ('tentative', 'Tentative'),
        ('waitlist', 'Waitlist')
    ]
    game = models.ForeignKey(
        ScheduleGame,
        on_delete=models.CASCADE,
        related_name='participants',
    )
    discord_user_id = models.BigIntegerField(
        'Discord User ID',
        null=True,
        blank=True,
    )
    name = models.TextField(
        'Имя'
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES
    )

    class Meta:
        unique_together = ('game', 'discord_user_id', 'name')


    def __str__(self):
        return self.name


class GameCellAssignment(Model):
    PAGE_CHOICES = [
        (1, 'Страница 1'),
        (2, 'Страница 2'),
    ]

    game = models.ForeignKey(
        ScheduleGame,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    participant = models.ForeignKey(
        GameParticipant,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    cell_index = models.IntegerField(
        'Индекс ячейки'
    )
    page_number = models.PositiveSmallIntegerField(
        'Номер страницы',
        choices=PAGE_CHOICES,
        default=1
    )
    role_icon = models.CharField(
        'Роль',
        max_length=120,
        blank=True,
        default=''
    )
    vehicle_icon = models.CharField(
        'Техника',
        max_length=120,
        blank=True,
        default=''
    )
    vehicle_color = models.CharField(
        'Цвет техники',
        max_length=7,
        blank=True,
        default='#ffffff'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['game', 'participant', 'page_number'],
                name='unique_player_per_game'
            ),
            models.UniqueConstraint(
                fields=['game', 'cell_index', 'page_number'],
                name='unique_cell_per_game'
            )
        ]
        verbose_name = 'Ячейки'

    def __str__(self):
        return f'{self.game} стр.{self.page_number} {self.participant} -> {self.cell_index}'
