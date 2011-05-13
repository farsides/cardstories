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
import os

from email.mime.text import MIMEText

from twisted.internet import defer
from twisted.enterprise import adbapi
from twisted.mail.smtp import sendmail

class Auth:

    def __init__(self, settings):
        self.settings = settings
        self.sendmail = sendmail
        database = self.settings['auth-db']
        exists = os.path.exists(database)
        if not exists:
            import sqlite3
            db = sqlite3.connect(database)
            c = db.cursor()
            c.execute(
                "CREATE TABLE players ( " 
                "  id INTEGER PRIMARY KEY, "
                "  name VARCHAR(255) " 
                "); ")
            c.execute(
                "CREATE INDEX players_idx ON players (name); "
                )
            db.commit()
            db.close()
        self.db = adbapi.ConnectionPool("sqlite3", database=database)

    def create(self, transaction, value):
        transaction.execute("INSERT INTO players (name) VALUES (?)", [ value ])
        return transaction.lastrowid
        
    @defer.inlineCallbacks
    def invite(self, game_id, player_ids):
        if game_id and player_ids:
            mails = filter(lambda player_id: '@' in player_id, player_ids)
            if len(mails) > 0:
                body = self.settings.get('mail-body', 'http://localhost:4923/static/?player_id=%(player_id)s&game_id=%(game_id)s')
                sender = self.settings.get('mail-from', 'cardstories')
                host = self.settings.get('mail-host', 'localhost')
                for mail in mails:
                    msg = MIMEText(body % { 'player_id': mail,
                                            'game_id': game_id[0] })
                    msg['Subject'] = self.settings.get('mail-subject', 'Cardstories invitation')
                    msg['From'] = sender
                    msg['To'] = mail
                    yield self.sendmail(host, sender, mail, msg.as_string())
        defer.returnValue(None)
        
    @defer.inlineCallbacks
    def preprocess(self, result, request):
        if request.args.get('action') == ['invite']:
            yield self.invite(request.args.get('game_id'), request.args.get('player_id'))
        for (key, values) in request.args.iteritems():
            if key == 'player_id' or key == 'owner_id':
                new_values = []
                for value in values:
                    row = yield self.db.runQuery("SELECT id FROM players WHERE name = ?", [ value ])
                    if len(row) == 0:
                        id = yield self.db.runInteraction(self.create, value)
                    else:
                        id = row[0][0]
                    new_values.append(id)
                request.args[key] = new_values
        defer.returnValue(result)

    @defer.inlineCallbacks
    def postprocess(self, result):
        if result.has_key('players'):
            for player in result['players']:
                row = yield self.db.runQuery("SELECT name FROM players WHERE id = ?", [ player[0] ])
                player[0] = row[0][0]
        defer.returnValue(result)

