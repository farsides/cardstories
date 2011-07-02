#
# Copyright (C) 2011 Loic Dachary <loic@dachary.org>
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

from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

from twisted.python import failure, runtime, log
from twisted.internet import defer, reactor
from twisted.mail.smtp import sendmail
from twisted.web import client

class Plugin:

    ALLOWED = ( 'invite', 'pick', 'voting', 'vote', 'complete' )

    def __init__(self, service, plugins):
        for plugin in plugins:
            if plugin.name() == 'auth':
                self.auth = plugin
                break
            elif plugin.name() == 'djangoauth':
                self.auth = plugin
                break
        assert self.auth
        self.service = service
        self.service.listen().addCallback(self.self_notify)
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], 'mail')
        dir = os.path.join(self.service.settings['plugins-dir'], 'mail')
        self.templates = {}
        for allowed in self.ALLOWED:
            f = open(os.path.join(dir, 'templates', allowed, 'template.html'))
            self.templates[allowed] = f.read()
            f.close()
        self.settings = objectify.parse(open(os.path.join(self.confdir, 'mail.xml'))).getroot()
        self.sender = self.settings.get('sender')
        self.host = self.settings.get('host')
        self.url = self.settings.get('url')
        self.static_url = self.settings.get('static_url')
        self.sendmail = sendmail

    def name(self):
        return 'mail'

    def self_notify(self, changes):
        d = defer.succeed(True)
        if changes != None and changes['type'] == 'change':
            details = changes['details']
            if details['type'] in self.ALLOWED:
                d = getattr(self, details['type'])(changes['game'], details)
        self.service.listen().addCallback(self.self_notify)
        return d

    @defer.inlineCallbacks
    def resolve(self, player_ids):
        if self.auth.name() == 'auth':
            rows = yield self.auth.db.runQuery("SELECT name FROM players WHERE " + ' OR '.join([ 'id = ?' ] * len(player_ids)), player_ids)
            usernames = map(lambda row: row[0], rows)
        elif self.auth.name() == 'djangoauth':
            usernames = []
            for player_id in player_ids:
                username = yield client.getPage("http://%s/getusername/%s/" % (self.auth.host, str(player_id)))
                usernames.append(username)
        defer.returnValue(usernames)

    @defer.inlineCallbacks
    def send(self, subject, recipients, template, variables):
        recipients = yield self.resolve(recipients)
        recipients = filter(lambda name: '@' in name, recipients)
        if len(recipients) == 0:
            defer.returnValue(False)
        else:
            email = MIMEMultipart("alternative")
            email['From'] = self.sender
            email['Subject'] = subject
            email['To'] = ', '.join(recipients)
            variables['url'] = self.url
            variables['static_url'] = self.static_url
            html = MIMEText(template % variables, 'html')
            email.attach(html)
            yield self.sendmail(self.host, self.sender, recipients, email.as_string())
            defer.returnValue(True)

    @defer.inlineCallbacks
    def pick_or_vote(self, game, player_id, subject, template):
        ( player_email, ) = yield self.resolve([ player_id ])
        yield self.send(subject, [ game.get_owner_id() ], template,
                        { 'game_id': game.get_id(),
                          'player_email': player_email
                          })

    def pick(self, game, details):
        return self.pick_or_vote(game, details['player_id'], "Cardstories - New card picked!", self.templates['pick'])

    def vote(self, game, details):
        return self.pick_or_vote(game, details['player_id'], "Cardstories - New vote!", self.templates['vote'])

    @defer.inlineCallbacks
    def invite(self, game, details):
        recipients = details['invited']
        ( owner_email, ) = yield self.resolve([ game.get_owner_id() ])
        yield self.send("Cardstories - You have been invited to a Game.", recipients, self.templates['invite'],
                        { 'game_id': game.get_id(),
                          'owner_email': owner_email
                          })
    
    @defer.inlineCallbacks
    def voting(self, game, details):
        recipients = game.get_players()
        recipients.remove(game.get_owner_id())
        yield self.send("Cardstories - you can vote.", recipients, self.templates['voting'],
                        { 'game_id': game.get_id() })
    
    @defer.inlineCallbacks
    def complete(self, game, details):
        ( owner_email, ) = yield self.resolve([ game.get_owner_id() ])
        yield self.send("Cardstories - Results.", game.get_players(), self.templates['complete'],
                        { 'game_id': game.get_id(),
                          'owner_email': owner_email
                          })

