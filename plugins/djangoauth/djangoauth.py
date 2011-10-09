#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Authors:
#          Loic Dachary <loic@dachary.org>
#          Adolfo R. Brandes <arbrandes@gmail.com>
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

from types import ListType

from twisted.python import log
from twisted.internet import defer
from twisted.web import client

class Plugin:

    def __init__(self, service, plugins):
        self.service = service
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], 'djangoauth')
        self.settings = objectify.parse(open(os.path.join(self.confdir, 'djangoauth.xml'))).getroot()
        self.host = self.settings.get('host')
        self.getPage = client.getPage
        log.msg('plugin djangoauth initialized')

    def name(self):
        return 'djangoauth'

    @defer.inlineCallbacks
    def create(self, name):
        id = yield self.getPage("http://%s/getuserid/%s/?create=yes" % (self.host, name))
        defer.returnValue(id)

    @defer.inlineCallbacks
    def resolve(self, id):
        name = yield self.getPage("http://%s/getusername/%s/" % (self.host, str(id)))
        defer.returnValue(name)

    @defer.inlineCallbacks
    def create_players(self, names):
        ids = []
        for name in names:
            id = yield self.create(name)
            ids.append(id)
        defer.returnValue(ids)

    @defer.inlineCallbacks
    def resolve_players(self, ids):
        names = []
        for id in ids:
            name = yield self.resolve(id)
            names.append(name)
        defer.returnValue(names)

    @defer.inlineCallbacks
    def preprocess(self, result, request):
        for (key, values) in request.args.iteritems():
            if key == 'player_id' or key == 'owner_id':
                new_values = []
                for value in values:
                    value = value.decode('utf-8')
                    # Invitation player_id's cannot be retrieved using the
                    # sessionid cookie, which only refers to the logged-in user.
                    if request.args.has_key('action') and \
                        request.args['action'][0] == 'invite' and \
                        key == 'player_id':
                        id = yield self.create(str(value))
                    # Otherwise, try to get the id from the session cookie.
                    else:
                        sessionid = request.getCookie('sessionid')
                        id = yield self.getPage("http://%s/getloggedinuserid/%s/" %
                                                (self.host, str(sessionid)))

                    id = int(id)
                    new_values.append(id)
                request.args[key] = new_values
        defer.returnValue(result)

    @defer.inlineCallbacks
    def postprocess(self, results):
        if type(results) is ListType:
            for result in results:
                if result.has_key('owner_id'):
                    result['owner_id'] = yield self.resolve(result['owner_id'])
                if result.has_key('players'):
                    for player in result['players']:
                        player[0] = yield self.resolve(player[0])
                if result.has_key('invited') and result['invited']:
                    invited = result['invited'];
                    for index in range(len(invited)):
                        invited[index] = yield self.resolve(invited[index])
                if result.has_key('messages'):
                    for message in result['messages']:
                        if message.has_key('player_id'):
                            message['player_id'] = yield self.resolve(message['player_id'])
        defer.returnValue(results)
