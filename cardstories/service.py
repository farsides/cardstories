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
import random

from twisted.python import log
from twisted.application import service
from twisted.internet import protocol, reactor, defer
from twisted.web import resource, client
from twisted.enterprise import adbapi

from OpenSSL import SSL

NCARDS = 36
NPLAYERS = 6
CARDS_PER_PLAYER = 7

class CardstoriesService(service.Service):

    def __init__(self, settings):
        self.settings = settings
        self.NCARDS = NCARDS
        self.NPLAYERS = NPLAYERS
        self.CARDS_PER_PLAYER = CARDS_PER_PLAYER

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
                "  owner_id INTEGER, " +
                "  players INTEGER DEFAULT 1, " +
                "  sentence TEXT, " +
                "  cards VARCHAR(%d), " % self.NCARDS +
                "  board VARCHAR(%d), " % self.NPLAYERS +
                "  state VARCHAR(8) DEFAULT 'invitation', " + # invitation, vote
                "  created DATETIME, " +
                "  completed DATETIME" +
                "); ")
            c.execute(
                "CREATE INDEX games_idx ON games (id); "
                )
            c.execute(
                "CREATE TABLE players ( " +
                "  id INTEGER PRIMARY KEY, " +
                "  name TEXT, " +
                "  created DATETIME " +
                "); ")
            c.execute(
                "CREATE INDEX players_idx ON players (id); "
                )
            c.execute(
                "CREATE TABLE player2game ( " +
                "  player_id INTEGER, " +
                "  game_id INTEGER, " +
                "  cards VARCHAR(%d), " % self.CARDS_PER_PLAYER +
                "  picked CHAR(1), " +
                "  vote CHAR(1), " +
                "  win CHAR(1) DEFAULT 'n' " +
                "); ")
            c.execute(
                "CREATE UNIQUE INDEX player2game_idx ON player2game (player_id, game_id); "
                )
            db.commit()
            db.close()
        self.db = adbapi.ConnectionPool("sqlite3", database=database)
        loop = self.settings.get('loop', 0)
        if loop != 0:
            return self.run(loop)
        
    def stopService(self):
        return defer.succeed(None)

    def createInteraction(self, transaction, card, sentence, owner_id):
        cards = [ chr(x) for x in range(1, self.NCARDS + 1) ]
        cards.remove(card)
        random.shuffle(cards)
        transaction.execute("INSERT INTO games (sentence, cards, board, owner_id, created) VALUES (?, ?, ?, ?, date('now'))", [sentence, ''.join(cards), card, owner_id])
        game_id = transaction.lastrowid
        transaction.execute("INSERT INTO player2game (game_id, player_id, cards, picked) VALUES (?, ?, ?, ?)", [ game_id, owner_id, card, card ])
        return game_id

    def create(self, args):
        card = chr(int(args['card'][0]))
        sentence = args['sentence'][0]
        owner_id = int(args['owner_id'][0])
        d = self.db.runInteraction(self.createInteraction, card, sentence, owner_id)
        d.addCallback(lambda game_id: {'game_id': game_id})
        return d

    def creationKit(self):
        d = defer.succeed(True)
        d.addCallback(lambda result: { 'cards': range(1, self.NCARDS + 1) })
        return d

    def participateInteraction(self, transaction, game_id, player_id):
        try:
            transaction.execute("SELECT players, cards FROM games WHERE id = %d" % game_id)
            ( players, cards ) = transaction.fetchall()[0]
            no_room = Exception('player %d cannot join game %d because the %d players limit is reached' % ( player_id, game_id, self.NPLAYERS ))
            if players >= self.NPLAYERS:
                raise no_room
            transaction.execute("UPDATE games SET cards = ?, players = players + 1 WHERE id = %d AND players = %d" % ( game_id, players ), [ cards[self.CARDS_PER_PLAYER:] ])
            if transaction.rowcount == 0:
                raise no_room
            transaction.execute("INSERT INTO player2game (game_id, player_id, cards) VALUES (?, ?, ?)", [ game_id, player_id, cards[:self.CARDS_PER_PLAYER] ])
            return {}
        except Exception, e:
            return {'error': e.args[0]}

    def participate(self, args):
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        return self.db.runInteraction(self.participateInteraction, game_id, player_id)

    @defer.inlineCallbacks
    def voting(self, args):
        game_id = int(args['game_id'][0])
        owner_id = int(args['owner_id'][0])
        rows = yield self.db.runQuery("SELECT picked FROM player2game WHERE game_id = %d AND picked IS NOT NULL")
        board = ''.join(map(lambda row: row[0], rows))
        yield self.db.runOperation("UPDATE games SET board = ?, state = 'voting' WHERE id = %d AND owner_id = %d" % ( game_id, owner_id ), [ board ])

    @defer.inlineCallbacks
    def player2game(self, args):
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        rows = yield self.db.runQuery("SELECT cards, picked, vote, win FROM player2game WHERE game_id = %d AND player_id = %d" % ( game_id, player_id ))
        def c(c):
            if c:
                return ord(c)
            else:
                return c
        defer.returnValue({ 'cards': map(lambda c: ord(c), rows[0][0]),
                            'picked': c(rows[0][2]),
                            'vote': c(rows[0][2]),
                            'win': rows[0][3] })

    def pick(self, args):
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        card = int(args['card'][0])
        return self.db.runOperation("UPDATE player2game SET picked = ? WHERE game_id = %d AND player_id = %d" % ( game_id, player_id ), [ chr(card) ])

    def tick(self):
        return defer.succeed(True)

    def run(self, count):
        self.completed = defer.Deferred()
        self.run_once(count)
        return self.completed

    def run_once(self, count):
        d = self.tick()
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
