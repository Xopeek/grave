from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('lineup/', include('lineup.urls')),
    path('login/', include('users.urls')),
    #path('accounts/', include('allauth.urls')),
    #path('discord/login/callback/')
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
