from django.contrib import admin
from .models import DiscordChannel, ScheduleGame, GameParticipant


admin.site.register(DiscordChannel)


class GameParticipantInline(admin.TabularInline):
    model = GameParticipant
    extra = 0
    fields = ('discord_user_id', 'status')
    readonly_fields = ()
    show_change_link = True


class ScheduleGameAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    list_filter = ('created_at',)
    inlines = [GameParticipantInline]


class GameParticipantAdmin(admin.ModelAdmin):
    list_display = ('name', 'game', 'status', 'discord_user_id')
    list_filter = ('status', 'game')


admin.site.register(ScheduleGame, ScheduleGameAdmin)
admin.site.register(GameParticipant, GameParticipantAdmin)