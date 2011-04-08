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

class CardstoriesService(service.Service):

    MIN_PICKED = 3 # there needs to be at least 3 cards to move to the voting phase
    NCARDS = 36
    NPLAYERS = 6
    CARDS_PER_PLAYER = 7
    ACTIONS = ( 'create', 'game', 'participate', 'voting', 'pick', 'vote', 'complete', 'invite', 'lobby' )

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
                "CREATE TABLE games ( " 
                "  id INTEGER PRIMARY KEY, "
                "  owner_id INTEGER, " 
                "  players INTEGER DEFAULT 1, "
                "  sentence TEXT, "
                "  cards VARCHAR(%d), " % self.NCARDS +
                "  board VARCHAR(%d), " % self.NPLAYERS +
                "  state VARCHAR(8) DEFAULT 'invitation', " + # invitation, vote, complete
                "  created DATETIME, " 
                "  completed DATETIME" 
                "); ")
            c.execute(
                "CREATE INDEX games_idx ON games (id); "
                )
            c.execute(
                "CREATE TABLE player2game ( "
                "  player_id INTEGER, "
                "  game_id INTEGER, " 
                "  cards VARCHAR(%d), " % self.CARDS_PER_PLAYER +
                "  picked CHAR(1), " 
                "  vote CHAR(1), " 
                "  win CHAR(1) DEFAULT 'n' "
                "); ")
            c.execute(
                "CREATE UNIQUE INDEX player2game_idx ON player2game (player_id, game_id); "
                )
            c.execute(
                "CREATE TABLE invitations ( "
                "  player_id INTEGER, "
                "  game_id INTEGER" 
                "); ")
            c.execute(
                "CREATE UNIQUE INDEX invitations_idx ON invitations (player_id, game_id); "
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
        self.required(args, 'create', 'card', 'sentence', 'owner_id')
        card = chr(int(args['card'][0]))
        sentence = args['sentence'][0]
        owner_id = int(args['owner_id'][0])
        d = self.db.runInteraction(self.createInteraction, card, sentence, owner_id)
        d.addCallback(lambda game_id: {'game_id': game_id})
        return d

    def deck(self):
        d = defer.succeed(True)
        d.addCallback(lambda result: { 'cards': range(1, self.NCARDS + 1) })
        return d

    @defer.inlineCallbacks
    def game(self, args):
        self.required(args, 'game', 'game_id')
        game_id = int(args['game_id'][0])
        if args.has_key('player_id'):
            player_id = int(args['player_id'][0])
        else:
            player_id = None
        rows = yield self.db.runQuery("SELECT owner_id, sentence, cards, board, state, created, completed FROM games WHERE id = ?", [game_id])
        ( owner_id, sentence, cards, board, state, created, completed ) = rows[0]
        if owner_id == player_id:
            cards = [ ord(c) for c in cards ]
        else:
            cards = None
        if owner_id != player_id and state == 'invitation':
            board = None
        else:
            board = [ ord(c) for c in board ]
        rows = yield self.db.runQuery("SELECT player_id, cards, picked, vote, win FROM player2game WHERE game_id = ? ORDER BY player_id", [ game_id ])
        picked_count = 0
        vote_count = 0
        players = []
        winner_card = None
        myself = None
        for player in rows:
            if player[0] == player_id or owner_id == player_id:
                player_cards = [ ord(c) for c in player[1] ]
            else:
                player_cards = None
            if player[2] != None and ( state == 'complete' or player[0] == player_id or owner_id == player_id ):
                picked = ord(player[2])
            else:
                picked = None
            if player[2] != None:
                picked_count += 1
            if player[0] == player_id:
                myself = [ self.ord(player[2]), self.ord(player[3]), player_cards ]
            if state == 'complete' or owner_id == player_id:
                if player[0] == owner_id:
                    winner_card = ord(player[1][0])
                vote = self.ord(player[3])
            else:
                vote = None
            if player[3] != None:
                vote_count += 1
            players.append([ player[0], vote, player[4], picked, player_cards ])
        ready = None
        if state == 'invitation':
            ready = picked_count >= self.MIN_PICKED
        elif state == 'vote':
            ready = picked_count == vote_count + 1 # + 1 is because the owner does not get to vote
        defer.returnValue({ 'id': game_id,
                            'sentence': sentence,
                            'winner_card': winner_card,
                            'cards': cards, 
                            'board': board, 
                            'state': state,
                            'ready': ready,
                            'self': myself,
                            'owner': owner_id == player_id,
                            'players': players })

    def participateInteraction(self, transaction, game_id, player_id):
        transaction.execute("SELECT players, cards FROM games WHERE id = %d" % game_id)
        ( players, cards ) = transaction.fetchall()[0]
        no_room = UserWarning('player %d cannot join game %d because the %d players limit is reached' % ( player_id, game_id, self.NPLAYERS ))
        if players >= self.NPLAYERS:
            raise no_room
        transaction.execute("UPDATE games SET cards = ?, players = players + 1 WHERE id = %d AND players = %d" % ( game_id, players ), [ cards[self.CARDS_PER_PLAYER:] ])
        if transaction.rowcount == 0:
            raise no_room
        transaction.execute("INSERT INTO player2game (game_id, player_id, cards) VALUES (?, ?, ?)", [ game_id, player_id, cards[:self.CARDS_PER_PLAYER] ])
        transaction.execute("DELETE FROM invitations WHERE game_id = ? AND player_id = ?", [ game_id, player_id ])
        return {}

    def participate(self, args):
        self.required(args, 'participate', 'player_id', 'game_id')
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        return self.db.runInteraction(self.participateInteraction, game_id, player_id)

    @defer.inlineCallbacks
    def voting(self, args):
        self.required(args, 'voting', 'owner_id', 'game_id')
        game_id = int(args['game_id'][0])
        owner_id = int(args['owner_id'][0])
        rows = yield self.db.runQuery("SELECT picked FROM player2game WHERE game_id = %d AND picked IS NOT NULL ORDER BY picked" % game_id)
        board = ''.join(card for (card,) in rows)
        yield self.db.runOperation("UPDATE games SET board = ?, state = 'vote' WHERE id = %d AND owner_id = %d" % ( game_id, owner_id ), [ board ])
        yield self.cancelInvitations(game_id)
        defer.returnValue({})

    @defer.inlineCallbacks
    def player2game(self, args):
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        rows = yield self.db.runQuery("SELECT cards, picked, vote, win FROM player2game WHERE game_id = %d AND player_id = %d" % ( game_id, player_id ))
        defer.returnValue({ 'cards': map(lambda c: ord(c), rows[0][0]),
                            'picked': self.ord(rows[0][2]),
                            'vote': self.ord(rows[0][2]),
                            'win': rows[0][3] })

    @defer.inlineCallbacks
    def pick(self, args):
        self.required(args, 'pick', 'player_id', 'game_id', 'card')
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        card = int(args['card'][0])
        yield self.db.runOperation("UPDATE player2game SET picked = ? WHERE game_id = %d AND player_id = %d" % ( game_id, player_id ), [ chr(card) ])
        defer.returnValue({})

    @defer.inlineCallbacks
    def vote(self, args):
        self.required(args, 'vote', 'player_id', 'game_id', 'card')
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        vote = int(args['card'][0])
        yield self.db.runOperation("UPDATE player2game SET vote = ? WHERE game_id = %d AND player_id = %d" % ( game_id, player_id ), [ chr(vote) ])
        defer.returnValue({})

    def completeInteraction(self, transaction, game_id, owner_id):
        transaction.execute("SELECT cards FROM player2game WHERE game_id = %d AND player_id = %d" % ( game_id, owner_id ))
        winner_card = transaction.fetchone()[0]
        transaction.execute("SELECT vote, player_id FROM player2game WHERE game_id = %d AND player_id != %d AND vote IS NOT NULL" % ( game_id, owner_id ))
        players_count = 0
        guessed = []
        failed = []
        for ( vote, player_id ) in transaction.fetchall():
            players_count += 1
            if vote == winner_card:
                guessed.append(player_id)
            else:
                failed.append(player_id)
        if len(guessed) > 0 and len(guessed) < players_count:
            winners = guessed + [ owner_id ]
        else:
            winners = failed + guessed
        transaction.execute("UPDATE player2game SET win = 'y' WHERE "
                            "  game_id = %d AND " % game_id + 
                            "  player_id IN ( %s ) " % ','.join([ str(id) for id in winners ]))
        transaction.execute("UPDATE games SET completed = date('now'), state = 'complete' WHERE id = %d" % game_id)
        return {}

    @defer.inlineCallbacks
    def complete(self, args):
        self.required(args, 'complete', 'owner_id', 'game_id')
        owner_id = int(args['owner_id'][0])
        game_id = int(args['game_id'][0])
        yield self.db.runInteraction(self.completeInteraction, game_id, owner_id)
        defer.returnValue({})

    def cancelInvitations(self, game_id):
        return self.db.runQuery("DELETE FROM invitations WHERE game_id = ?", [ game_id ])

    @defer.inlineCallbacks
    def invite(self, args):
        self.required(args, 'invite', 'owner_id', 'player_id', 'game_id')
        game_id = args['game_id'][0]
        for player_id in args['player_id']:
            yield self.db.runQuery("INSERT INTO invitations (player_id, game_id) VALUES (?, ?)", [ player_id, game_id ])
        defer.returnValue({})

    @staticmethod
    def ord(c):
        if c:
            return ord(c)
        else:
            return c

    @staticmethod
    def required(args, method, *keys):
        for key in keys:
            if not args.has_key(key):
                raise UserWarning, '%s must be given a %s value' % ( method, key )
        return True

    @defer.inlineCallbacks
    def lobby(self, args):
        self.required(args, 'lobby', 'player_id', 'in_progress')
        if args['in_progress'][0] == 'true':
            complete = 'state != "complete"'
        else:
            complete = 'state = "complete"'
        order = " ORDER BY created DESC"
        if args.has_key('my') and args['my'][0] == 'true':
            sql =  ""
            sql += " SELECT id, sentence, state, owner_id = player_id, created FROM games, player2game WHERE player2game.player_id = ? AND " + complete + " AND games.id = player2game.game_id"
            sql += " UNION "
            sql += " SELECT id, sentence, state, owner_id = player_id, created FROM games, invitations WHERE invitations.player_id = ? AND " + complete + " AND games.id = invitations.game_id"
            sql += order
            games = yield self.db.runQuery(sql, [ args['player_id'][0], args['player_id'][0] ])
        else:
            sql = "SELECT id, sentence, state, owner_id = ?, created FROM games WHERE " + complete
            sql += order
            games = yield self.db.runQuery(sql, [ args['player_id'][0] ])
        sql = "SELECT id, win FROM games, player2game WHERE player2game.player_id = ? AND " + complete + " AND games.id = player2game.game_id"
        rows = yield self.db.runQuery(sql, [ args['player_id'][0] ])
        wins = {}
        for row in rows:
            wins[row[0]] = row[1]
        defer.returnValue({'games': games,
                           'win': wins})

    def handle(self, args):
        if not args.has_key('action'):
            return defer.succeed({})
        try:
            action = args['action'][0]
            if action in self.ACTIONS:
                d = getattr(self, action)(args)
                def error(reason):
                    if reason.type is UserWarning:
                        return {'error': reason.getErrorMessage()}
                    else:
                        return reason
                d.addErrback(error)
                return d
            else:
                raise UserWarning('action ' + action + ' is not among the allowed actions ' + ','.join(self.ACTIONS))
        except UserWarning, e:
            return defer.succeed({'error': e.args[0]})

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
