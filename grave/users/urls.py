from django.urls import path

from users import views


urlpatterns = [
    path('discord/', views.discord_login, name='discord_login'),
    path('discord/callback/', views.discord_callback, name='discord_callback'),
    path('logout/', views.logout_view, name='logout'),
]
