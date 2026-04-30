import json
import secrets
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model, login, logout
from django.contrib.sessions.models import Session
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.conf import settings
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from yarl import URL

from users.models import DiscordAccount


DISCORD_HTTP_HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'grave-app/1.0 (+http://128.0.0.1)',
}


def _exchange_code_for_token(code, redirect_url):
    payload = {
        'client_id': settings.DISCORD_CLIENT_ID,
        'client_secret': settings.DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_url,
    }

    request = Request(
        settings.DISCORD_TOKEN_URL,
        data=urlencode(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            **DISCORD_HTTP_HEADERS,
        },
        method='POST'
    )

    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


def _fetch_discord_user(access_token):
    request = Request(
        settings.DISCORD_USER_URL,
        headers={
            'Authorization': f'Bearer {access_token}',
            **DISCORD_HTTP_HEADERS,
        },
        method='GET'
    )

    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


def _http_error_details(error: HTTPError):
    body = ''
    try:
        body = error.read().decode('utf-8', errors='replace')
    except Exception:
        pass
    return f'HTTP Error {error.code}: {error.reason}. {body}'.strip()


def _get_or_create_local_user(discord_user):
    user_model = get_user_model()

    discord_id = int(discord_user['id'])
    username = f'discord_{discord_id}'
    global_name = discord_user.get('global_name') or ''
    discord_username = discord_user.get('username') or ''
    avatar = discord_user.get('avatar') or ''

    user, created = user_model.objects.get_or_create(
        username=username,
        defaults={
            'first_name': global_name or discord_username,
        },
    )

    display_name = global_name or discord_username
    updated_fields= []

    if display_name and user.first_name != display_name:
        user.first_name = display_name
        updated_fields.append('first_name')


    if hasattr(user, 'is_active') and not user.is_active:
        user.is_active = True
        updated_fields.append('is_active')

    if user.has_usable_password():
        user.set_unusable_password()
        updated_fields.append('password')

    if created:
        user.save()
    elif updated_fields:
        user.save(update_fields=updated_fields)

    DiscordAccount.objects.update_or_create(
        discord_id=discord_id,
        defaults={
            'user': user,
            'discord_username': discord_username,
            'discord_global_name': global_name,
            'discord_avatar': avatar,
        },
    )

    return user


@require_GET
def discord_login(request):
    state = secrets.token_urlsafe(32)
    request.session['discord_oauth_state'] = state

    next_url = request.GET.get('next') or settings.LOGIN_REDIRECT_URL or '/'
    request.session['discord_next_url'] = next_url

    redirect_url = request.build_absolute_uri(reverse('discord_callback'))

    params = {
        'response_type': 'code',
        'client_id': settings.DISCORD_CLIENT_ID,
        'scope': settings.DISCORD_SCOPE,
        'redirect_uri': redirect_url,
        'state': state,
    }

    auth_url = f'{settings.DISCORD_AUTHORIZE_URL}?{urlencode(params)}'
    return redirect(auth_url)


@require_GET
def discord_callback(request):
    error = request.GET.get('error')

    if error:
        return HttpResponseBadRequest(f'Discord auth error: {error}')

    code = request.GET.get('code')
    state = request.GET.get('state')

    saved_state = request.session.get('discord_oauth_state')

    if not code or not state or not saved_state or state != saved_state:
        return HttpResponseBadRequest('Invalid OAuth state')

    request.session.pop('discord_oauth_state', None)
    redirect_url = request.build_absolute_uri(reverse('discord_callback'))

    try:
        token_data = _exchange_code_for_token(code, redirect_url)
        access_token = token_data['access_token']
        discord_user = _fetch_discord_user(access_token)
    except HTTPError as e:
        return HttpResponseBadRequest(
            f'could not complete Discord login: {_http_error_details(e)}'
        )
    except (URLError, KeyError, ValueError, json.JSONDecodeError) as e:
        return HttpResponseBadRequest(f'could not complete Discord login: {e}')

    user = _get_or_create_local_user(discord_user)
    login(request, user)
    request.session.save()

    next_url = request.session.pop('discord_next_url', '/')

    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = '/'

    return redirect(next_url)


@require_POST
def logout_view(request):
    logout(request)
    return redirect('/lineup/games/')
