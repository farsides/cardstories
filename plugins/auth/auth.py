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

from types import ListType

from twisted.python import log
from twisted.internet import defer
from twisted.enterprise import adbapi

class Plugin:

    def __init__(self, service, plugins):
        dirname = os.path.join(service.settings['plugins-libdir'], self.name())
        self.database = os.path.join(dirname, 'auth.sqlite')
        exists = os.path.exists(self.database)
        if not exists:
            if not os.path.exists(dirname):
                os.mkdir(dirname)
            import sqlite3
            db = sqlite3.connect(self.database)
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
        self.db = adbapi.ConnectionPool("sqlite3", database = self.database, cp_noisy = True)
        log.msg('plugin auth initialized with ' + self.database)

    def name(self):
        return 'auth'

    def create(self, transaction, value):
        transaction.execute("INSERT INTO players (name) VALUES (?)", [ value ])
        return transaction.lastrowid
        
    @defer.inlineCallbacks
    def resolve(self, id):
        row = yield self.db.runQuery("SELECT name FROM players WHERE id = ?", [ id ])
        defer.returnValue(row[0][0])

    @defer.inlineCallbacks
    def create_players(self, names):
        ids = []
        for name in names:
            id = yield self.db.runInteraction(self.create, name)
            ids.append(id)
        defer.returnValue(ids)

    @defer.inlineCallbacks
    def resolve_players(self, ids):
        rows = yield self.db.runQuery("SELECT name FROM players WHERE " + ' OR '.join([ 'id = ?' ] * len(ids)), ids)
        names = map(lambda row: row[0], rows)
        defer.returnValue(names)

    @defer.inlineCallbacks
    def preprocess(self, result, request):
        for (key, values) in request.args.iteritems():
            if key == 'player_id' or key == 'owner_id':
                new_values = []
                for value in values:
                    value = value.decode('utf-8')
                    row = yield self.db.runQuery("SELECT id FROM players WHERE name = ?", [ value ])
                    if len(row) == 0:
                        id = yield self.db.runInteraction(self.create, value)
                    else:
                        id = row[0][0]
                    new_values.append(id)
                request.args[key] = new_values
        defer.returnValue(result)

    @defer.inlineCallbacks
    def postprocess(self, results):
        if type(results) is ListType:
            for result in results:
                if result.has_key('players'):
                    for player in result['players']:
                        player[0] = yield self.resolve(player[0])
                if result.has_key('owner_id'):
                        result['owner_id'] = yield self.resolve(result['owner_id'])
                if result.has_key('invited') and result['invited']:
                    invited = result['invited'];
                    for index in range(len(invited)):
                        invited[index] = yield self.resolve(invited[index])
                if result.has_key('messages'):
                    for message in result['messages']:
                        if message.has_key('player_id'):
                            message['player_id'] = yield self.resolve(message['player_id'])
        defer.returnValue(results)

