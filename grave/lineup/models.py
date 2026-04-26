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