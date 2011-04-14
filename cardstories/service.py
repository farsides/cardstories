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

from twisted.python import log, runtime
from twisted.application import service
from twisted.internet import reactor, defer
from twisted.web import resource, client
from twisted.enterprise import adbapi

from cardstories.game import CardstoriesGame
from cardstories.player import CardstoriesPlayer

from OpenSSL import SSL

import sqlite3

from cardstories.poll import pollable

class CardstoriesPlayer(pollable):
    
    def __init__(self, service, id):
        self.service = service
        self.settings = service.settings
        self.id = id
        pollable.__init__(self, self.settings.get('poll-timeout', 300))

    def touch(self, args):
        args['player_id'] = [self.id]
        return pollable.touch(self, args)

class CardstoriesService(service.Service):

    ACTIONS_GAME = ( 'game', 'participate', 'voting', 'pick', 'vote', 'complete', 'invite' )
    ACTIONS = ACTIONS_GAME + ( 'create', 'lobby' )

    def __init__(self, settings):
        self.settings = settings
        self.games = {}
        self.players = {}

    def startService(self):
        database = self.settings['db']
        exists = os.path.exists(database)
        db = sqlite3.connect(database)
        c = db.cursor()
        if exists:
            self.load(c)
        else:
            self.create_base(c)
            db.commit()
        c.close()
        db.close()
        self.db = adbapi.ConnectionPool("sqlite3", database=database)
        loop = self.settings.get('loop', 0)
        if loop != 0:
            return self.run(loop)
        
    def stopService(self):
        for game in self.games.values():
            game.destroy()
        for player in self.players.values():
            if player.timer.active():
                player.timer.cancel()
            player.destroy()
        return defer.succeed(None)

    def create_base(self, c):
        c.execute(
            "CREATE TABLE games ( " 
            "  id INTEGER PRIMARY KEY, "
            "  owner_id INTEGER, " 
            "  players INTEGER DEFAULT 1, "
            "  sentence TEXT, "
            "  cards VARCHAR(%d), " % CardstoriesGame.NCARDS +
            "  board VARCHAR(%d), " % CardstoriesGame.NPLAYERS +
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
            "  cards VARCHAR(%d), " % CardstoriesGame.CARDS_PER_PLAYER +
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

    def load(self, c):
        c.execute("SELECT id FROM games WHERE state != 'complete'")
        for (id,) in c.fetchall():
            game = CardstoriesGame(self, id)
            game.load(c)
            self.games[id] = game
            
    def poll(self, args):
        self.required(args, 'poll', 'modified')
        if args.has_key('game_id'):
            return self.game_proxy(args)
        elif args.has_key('player_id'):
            return self.poll_player(args)
        else:
            raise UserWarning, 'poll requires either player_id or game_id but neither were set'

    def poll_player(self, args):
        player_id = int(args['player_id'][0])
        return self.get_or_create_player(player_id).poll(args)

    def get_or_create_player(self, player_id):
        now = int(runtime.seconds() * 1000)
        if not self.players.has_key(player_id):
            player = CardstoriesPlayer(self, player_id)
            player.access_time = now
            self.players[player_id] = player
            def timeout():
                if not self.players.has_key(player_id):
                    return False
                player = self.players[player_id]
                if now - player.access_time > self.settings.get('poll-timeout', 300) * 2:
                    player.touch({'delete': [now]})
                    del self.players[player_id]
                else:
                    player.timer = reactor.callLater(self.settings.get('poll-timeout', 300), timeout)
                return True
            timeout()
        else:
            player = self.players[player_id]
            player.access_time = now
        return player

    def poll_notify_players(self, args):
        if args == None:
            return False
        game_id = int(args['game_id'][0])
        if not self.games.has_key(game_id):
            return False
        game = self.games[game_id]
        for player_id in game.get_players():
            if self.players.has_key(player_id):
                self.players[player_id].touch(args)
        d = game.poll(args)
        d.addCallback(self.poll_notify_players)
        return True

    def create(self, args):
        game = CardstoriesGame(self)
        d = game.create(args)
        def success(value):
            self.games[game.get_id()] = game
            args['modified'] = [ game.modified ]
            args['game_id'] = [ game.id ]
            self.poll_notify_players(args)
            return value
        d.addCallback(success)
        return d

    def complete(self, args):
        d = self.game_proxy(args)
        game_id = int(args['game_id'][0])
        def success(value):
            self.games[game_id].destroy()
            del self.games[game_id]
            return value
        d.addCallback(success)
        return d

    def game(self, args):
        game_id = self.required_game_id(args)
        if self.games.has_key(game_id):
            game = self.games[game_id]
        else:
            game = CardstoriesGame(self, self.required_game_id(args))
        return game.game(args)

    def game_proxy(self, args):
        game_id = self.required_game_id(args)
        if not self.games.has_key(game_id):
            raise UserWarning, 'game_id=%s does not exist' % args['game_id']
        return getattr(self.games[game_id], args['action'][0])(args)

    participate = game_proxy
    player2game = game_proxy
    voting = game_proxy
    pick = game_proxy
    vote = game_proxy
    invite = game_proxy

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

    @staticmethod
    def required(args, method, *keys):
        for key in keys:
            if not args.has_key(key):
                raise UserWarning, '%s must be given a %s value' % ( method, key )
        return True

    @staticmethod
    def required_game_id(args):
        if not args.has_key('game_id'):
            raise UserWarning, '%s must be given a game_id value' % args['action'][0]
        game_id = int(args['game_id'][0])
        if game_id <= 0:
            raise UserWarning, 'game_id=%s must be an integer > 0' % args['game_id']
        return game_id

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
