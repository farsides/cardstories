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

from twisted.python import log
from twisted.application import service
from twisted.internet import protocol, reactor, defer
from twisted.web import resource, client
from twisted.enterprise import adbapi

from OpenSSL import SSL

class CardstoriesService(service.Service):

    def __init__(self, settings):
        self.settings = settings

    def startService(self):
        database = self.settings['db']
        exists = os.path.exists(database)
        if not exists:
            import sqlite3
            db = sqlite3.connect(database)
            c = db.cursor()
            c.execute(
                "CREATE TABLE games ( " +
                "  id INTEGER PRIMARY KEY, " +
                "  card TINYINT, " +
                "  sentence TEXT, " +
                "  state VARCHAR(8) DEFAULT 'picking', " +
                "  created DATETIME, " +
                "  completed DATETIME" +
                "); ")
            c.execute(
                "CREATE INDEX games ON games (id); "
                )
            db.commit()
            db.close()
        self.db = adbapi.ConnectionPool("sqlite3", database=database)
        loop = self.settings.get('loop', 0)
        if loop != 0:
            return self.run(loop)
        
    def stopService(self):
        return defer.succeed(None)

    def create(self, args):
        d = self.db.runOperation("INSERT INTO games (card, sentence, created) VALUES (?, ?, date('now'))", [args['url'][0], args['sentence'][0]])
        d.addCallback(lambda result: {})
        return d

    def autocomplete(self):
        pass

    def run(self, count):
        self.completed = defer.Deferred()
        self.run_once(count)
        return self.completed

    def run_once(self, count):
        d = self.autocomplete()
        count -= 1
        def again(result):
            if count != 0:
                reactor.callLater(self.settings.get('click', 60), lambda: self.run_once(count))
            else:
                self.completed.callback(True)
        d.addCallback(again)

class SSLContextFactory:

    def __init__(self, settings):
        self.pem_file = settings['ssl-pem']

    def getContext(self):
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file(self.pem_file)
        ctx.use_privatekey_file(self.pem_file)
        return ctx
