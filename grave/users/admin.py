from django.contrib import admin
from django.contrib.sessions.models import Session

from users.models import DiscordAccount

admin.site.register(DiscordAccount)
admin.site.register(Session)