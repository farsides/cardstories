# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Authors:
#          Adolfo R. Brandes <arbrandes@gmail.com>
#          Xavier Antoviaque <xavier@antoviaque.org>
#          Matjaz Gregoric <mtyaka@gmail.com>
#          Loic Dachary <loic@dachary.org>
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
from lxml import objectify
import os

from twisted.python import log
from twisted.internet import defer
from twisted.web import client

from cardstories.auth import Auth, AuthenticationError



class Plugin(Auth):

    def __init__(self, service, plugins):
        self.service = service
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], 'djangoauth')
        self.settings = objectify.parse(open(os.path.join(self.confdir, 'djangoauth.xml'))).getroot()
        self.host = self.settings.get('host')
        self.getPage = client.getPage
        self.id2name = {}
        self.id2email = {}
        self.id2avatar_url = {}
        self.email2id = {}
        log.msg('plugin djangoauth initialized')

    def name(self):
        return 'djangoauth'

    @defer.inlineCallbacks
    def get_player_id(self, email, create=False):
        # Use cache if available
        if email in self.email2id:
            id = self.email2id[email]
        else:
            create_query = ''
            if create:
                create_query += '?create=yes'
            id = yield self.getPage("http://%s/get_player_id/%s/%s" % (self.host, email, create_query))
            id = int(id)
            self.email2id[email] = id
        defer.returnValue(id)

    @defer.inlineCallbacks
    def get_player_name(self, id):
        # Use cache if available
        if id in self.id2name:
            name = self.id2name[id]
        else:
            name = yield self.getPage("http://%s/get_player_name/%s/" % (self.host, str(id)))
            self.id2name[id] = name
        defer.returnValue(name)

    @defer.inlineCallbacks
    def get_player_email(self, id):
        # Use cache if available
        if id in self.id2email:
            email = self.id2email[id]
        else:
            email = yield self.getPage("http://%s/get_player_email/%s/" % (self.host, str(id)))
            self.id2email[id] = email
        defer.returnValue(email)

    @defer.inlineCallbacks
    def get_player_avatar_url(self, id):
        # Use cache if available
        if id in self.id2avatar_url:
            avatar_url = self.id2avatar_url[id]
        else:
            avatar_url = yield self.getPage("http://%s/get_player_avatar_url/%s/" % (self.host, str(id)))
            self.id2avatar_url[id] = avatar_url
        defer.returnValue(avatar_url)

    @defer.inlineCallbacks
    def authenticate(self, request, requested_player_id):
        '''Ensure that the player_id match the request's session'''

        sessionid = request.getCookie('sessionid')
        cookie_player_id = yield self.getPage("http://%s/get_loggedin_player_id/%s/" % (self.host, str(sessionid)))
        requested_player_id = requested_player_id

        if requested_player_id != cookie_player_id:
            raise AuthenticationError(requested_player_id, cookie_player_id)

        defer.returnValue(True)
