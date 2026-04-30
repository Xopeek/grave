from django.conf import settings
from django.db import models


class DiscordAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discord_account',
    )
    discord_id = models.BigIntegerField(
        'Discord ID',
        unique=True,
        db_index=True,
    )
    discord_username = models.CharField(
        'Discord Username',
        max_length=100,
        blank=True,
        default=''
    )
    discord_global_name = models.CharField(
        'Discord Global Name',
        max_length=100,
        blank=True,
        default=''
    )
    discord_avatar = models.CharField(
        'Discord Avatar hash',
        max_length=255,
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(
        'Создано',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Обновлено',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Дискорд Аккаунт'
        verbose_name_plural = 'Дискорд Аккаунты'

    def __str__(self):
        return f'{self.discord_username} ({self.discord_id})'
