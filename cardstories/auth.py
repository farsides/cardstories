#
# Copyright (C) 2011 Dachary <loic@dachary.org>
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

from twisted.internet import defer
from twisted.enterprise import adbapi

class Auth:

    def __init__(self, settings):
        self.settings = settings
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
    def preprocess(self, result, request):
        for (key, value) in request.args.iteritems():
            if key == 'player_id' or key == 'owner_id':
                row = yield self.db.runQuery("SELECT id FROM players WHERE name = ?", [ value[0] ])
                if len(row) == 0:
                    id = yield self.db.runInteraction(self.create, value[0])
                else:
                    id = row[0][0]
                request.args[key] = [ id ]
        defer.returnValue(result)

    @defer.inlineCallbacks
    def postprocess(self, result):
        if result.has_key('players'):
            for player in result['players']:
                row = yield self.db.runQuery("SELECT name FROM players WHERE id = ?", [ player[0] ])
                player[0] = row[0][0]
        defer.returnValue(result)

