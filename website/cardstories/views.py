#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Author: Adolfo R. Brandes <arbrandes@gmail.com>
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation (FSF), either version 3 of the License, or (at your
# option) any later version of the AGPL published by the FSF.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program in a file in the toplevel directory called
# "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
#
from urllib import quote, urlencode, urlopen
from urlparse import parse_qs
from simplejson import loads, dumps

from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseNotFound, \
    HttpResponseForbidden
from django.http import HttpResponseBadRequest
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.sites.models import Site
from django.template import RequestContext
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import redirect

import paypal.standard.pdt.views
from paypal.standard.forms import PayPalPaymentsForm

from forms import RegistrationForm, LoginForm

from avatar import Avatar, GravatarAvatar, FacebookAvatar

def get_base_url(request):
    domain = Site.objects.get_current().domain
    return 'http://%s' % domain

def get_game_info(request):
    game_info = {}
    game_id = request.GET.get('game_id', '')
    if game_id != '':
        params = {'action': 'state',
                  'type': 'game',
                  'modified': 0,
                  'game_id': game_id}
        url = 'http://%s/resource?%s' % (settings.CARDSTORIES_HOST,
                                         urlencode(params))
        data = urlopen(url).read()
        response = loads(data)
        try:
            game_info = response[0]
        except KeyError:
            pass

    return game_info

def get_gameid_query(request):
    query = ''
    if request.GET.get('game_id', '') != '':
        query += '?game_id=' + request.GET['game_id']

    return query

def get_game_url(request):
    return "%s/%s" % (get_base_url(request), get_gameid_query(request))

def get_facebook_redirect_uri(request, encode=True):
    """
    Returns the urllib.quoted facebook redirection URI.

    """
    uri = '%s%s%s' % (get_base_url(request),
                      reverse(facebook),
                      get_gameid_query(request))

    if encode:
        uri = quote(uri, '')

    return uri

# If user's first_name attribute is not blank, it returns it's contents.
# Otherwise returns the first part of email (up to the @ character).
def get_user_display_name(user):
    # We are only using the first_name field, which may actually store
    # a full name/nickname/whatever.
    name = user.first_name and user.first_name.strip()
    if not name:
        name = user.email.split('@')[0]
    return name

def common_variables(request):
    """
    Common template variables.

    """
    return {'base_url': get_base_url(request),
            'gameid_query': get_gameid_query(request),
            'game_info': get_game_info(request),
            'game_url': get_game_url(request),
            'fb_redirect_uri': get_facebook_redirect_uri(request),
            'fb_app_id': settings.FACEBOOK_APP_ID,
            'owa_enable': settings.OWA_ENABLE,
            'owa_url': settings.OWA_URL,
            'owa_site_id': settings.OWA_SITE_ID}

def welcome(request):
    """
    Renders the welcome page, with either registration and
    login forms, or the game itself.

    """

    if request.user.is_authenticated():
        template = 'cardstories/game.html'
        context = {'create': request.session.get('create', False),
                   'player_id': request.user.id}
        request.session['create'] = False
    else:
        context = {'registration_form': RegistrationForm(),
                   'login_form': LoginForm()}
        template = 'cardstories/welcome.html'

    return render_to_response(template, context,
                              context_instance=RequestContext(request,
                              processors=[common_variables]))

def register(request):
    """
    Registers a user from supplied username and password.  If successful, logs
    the user in and redirects him to the cardstories client, with the proper
    cookie set.

    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']

            # Store username both as username and email, since username = email
            # for now.
            u = User.objects.create_user(username, username, password)
            u.first_name = name
            u.save()

            # Always call authenticate() before login().
            auth_user = authenticate(username=username, password=password)
            auth_login(request, auth_user)

            GravatarAvatar(auth_user).update()

            # The user was just created.
            request.session['create'] = True

            # Redirect maintaining game_id, if set.
            url = '%s%s' % (reverse(welcome), get_gameid_query(request))
            return redirect(url);
    else:
        form = RegistrationForm()

    context = {'registration_form': form,
               'login_form': LoginForm()}
    return render_to_response('cardstories/welcome.html', context,
                              context_instance=RequestContext(request,
                              processors=[common_variables]))

def login(request):
    """
    Logs a user in using Django's contrib.auth, and sets the cookie that
    the cardstories client expects.

    """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            # At this point, the user has already been authenticated by form
            # validation (which simplifies user feedback on login errors).
            auth_login(request, form.auth_user)

            GravatarAvatar(form.auth_user).update()

            # Redirect maintaining game_id, if set.
            url = '%s%s' % (reverse(welcome), get_gameid_query(request))
            return redirect(url);
    else:
        form = LoginForm()

    context = {'registration_form': RegistrationForm(),
               'login_form': form}
    return render_to_response('cardstories/welcome.html', context,
                              context_instance=RequestContext(request,
                              processors=[common_variables]))

def facebook(request):
    """
    Logs a user in using Facebook.  Registers the user using his/her email, so
    appropriate permissions are necessary.

    """
    if request.method == 'GET':
        if request.GET.get('error', '') == '' \
           and request.GET.get('code', '') != '':
            params = {
                'client_id': settings.FACEBOOK_APP_ID,
                'client_secret': settings.FACEBOOK_API_SECRET,
                'redirect_uri': get_facebook_redirect_uri(request, encode=False),
                'code': request.GET['code'],
            }

            url = 'https://graph.facebook.com/oauth/access_token?%s' % urlencode(params)
            data = urlopen(url).read()
            if 'error' not in data:
                response = parse_qs(data)
                token = response['access_token'][0]

                # authenticate() tries with all available authentication backends
                # Here it will be against the Facebook backend, which includes
                # an automatic registration of the user account based on FB data
                user = authenticate(token=token)

                if user and user.is_active:
                    auth_login(request, user)

                    FacebookAvatar(user).update()

                    # Signal that the user was created
                    request.session['create'] = True

                    # Redirect maintaining game_id, if set.
                    url = '%s%s' % (reverse(welcome), get_gameid_query(request))
                    return redirect(url);

    context = {'registration_form': RegistrationForm(),
               'login_form': LoginForm()}
    return render_to_response('cardstories/welcome.html', context,
                              context_instance=RequestContext(request,
                              processors=[common_variables]))

def logout(request):
    '''De-authenticate the user, if it was authenticated, and redirect
    him to the homepage'''

    auth_logout(request)

    url = reverse(welcome)
    return redirect(url)

def get_player_id(request, username):
    """
    Returns a user's id based on supplied username, optionally creating the
    user, if so requested.  Username will be validated according to
    registration form rules.
    
    If user is not found, a status of 404 will be returned.

    If user is not found, creation is requested, but the supplied username is
    invalid, a status of 400 will be returned.

    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        if request.GET.get('create', '') == 'yes':
            # Validates the username according to the registration form.
            name = "Cardstories Player"
            password = "mockpassword"
            data = {"name": name,
                    "username": username,
                    "password1": password,
                    "password2": password}
            form = RegistrationForm(data)
            if not form.is_valid():
                return HttpResponseBadRequest()

            # Create the user with an unusable password. The user will need
            # to click on "forgot password" to obtain a new one.
            user = User.objects.create_user(username, username)
            user.save()
        else:
            return HttpResponseNotFound()

    response = HttpResponse(user.id, mimetype="text/plain")
    return response

def get_player_name(request, userid):
    """
    Returns a user's name based on supplied id, if found.
    Returns 404 if not found.
    """
    try:
        user = User.objects.get(id=userid)
        return HttpResponse(get_user_display_name(user), mimetype="text/plain")
    except User.DoesNotExist:
        return HttpResponseNotFound()

def get_player_email(request, userid):
    """
    Returns a user's email (= username) based on supplied id, if found.
    Returns 404 if not found.
    """

    # Only the webservice should be able to retreive a player's email
    if request.META['REMOTE_ADDR'] != settings.WEBSERVICE_IP:
        return HttpResponseForbidden()

    try:
        user = User.objects.get(id=userid)
        return HttpResponse(user.username, mimetype="text/plain")
    except User.DoesNotExist:
        return HttpResponseNotFound()

def get_player_avatar_url(request, userid):
    """
    Returns a user's avatar URL, and create/retreive it from gravatar if none yet
    Returns 404 if the user is not found.
    """
    try:
        user = User.objects.get(id=userid)

        avatar = Avatar(user)
        if not avatar.in_cache():
            avatar = GravatarAvatar(user)
            avatar.update()

        return HttpResponse(avatar.get_url(), mimetype="text/plain")
    except User.DoesNotExist:
        return HttpResponseNotFound()

def get_loggedin_player_id(request, session_key):
    """
    Returns a user's id based on a logged in session id. If user is not found,
    a status of 404 will be returned.

    """
    try:
        session = Session.objects.get(session_key=session_key)
        user_id = session.get_decoded().get('_auth_user_id')
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, Session.DoesNotExist):
        return HttpResponseNotFound()

    response = HttpResponse(user.id, mimetype="text/plain")
    return response

def get_extra_cards_form(request):
    """
    Displays a HTML view with a form where the user can buy a pack of
    extra cards via paypal.
    """
    if request.user.is_authenticated():
        custom_data = {'player_id': request.user.id}

        paypal_dict = {
            'business': settings.PAYPAL_RECEIVER_EMAIL,
            'amount': settings.CS_EXTRA_CARD_PACK_PRICE,
            'currency_code': settings.CS_EXTRA_CARD_PACK_CURRENCY,
            'item_name': 'CardStories Extra Card Pack',
            'item_number': settings.CS_EXTRA_CARD_PACK_ITEM_ID,
            'notify_url': '%s/%s' % (settings.BASE_URL, settings.PAYPAL_IPN_PATH),
            'cancel_return': settings.BASE_URL,
            'custom':  dumps(custom_data),
        }

        form = PayPalPaymentsForm(initial=paypal_dict)
        context = {'form': form}
    else:
        context = {'form': None}

    return render_to_response('cardstories/get_extra_cards.html', context)

def after_bought_cards(request):
    return paypal.standard.pdt.views.pdt(request, template='cardstories/after_bought_cards.html')
