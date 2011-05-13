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
import random

from twisted.python import log, runtime
from twisted.application import service
from twisted.internet import reactor, defer
from twisted.web import resource, client
from twisted.enterprise import adbapi

from cardstories.game import CardstoriesGame

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
    ACTIONS = ACTIONS_GAME + ( 'create', 'lobby', 'poll' )

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
        c.execute("SELECT id FROM games WHERE state != 'complete' AND state != 'canceled'")
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
        if not self.players.has_key(player_id):
            player = CardstoriesPlayer(self, player_id)
            player.access_time = int(runtime.seconds() * 1000)
            #
            # modified time is set to the most recent
            # modification time of a game in which the player is
            # involved
            #
            player.set_modified(0)
            for game in self.games.values():
                if player_id in game.get_players():
                    if player.get_modified() < game.get_modified():
                        player.set_modified(game.get_modified())
            self.players[player_id] = player
            poll_timeout = self.settings.get('poll-timeout', 300)
            def timeout():
                now = int(runtime.seconds() * 1000)
                if not self.players.has_key(player_id):
                    return False
                player = self.players[player_id]
                if now - player.access_time > (poll_timeout * 2 * 1000):
                    player.touch({'delete': [now]})
                    del self.players[player_id]
                else:
                    player.timer = reactor.callLater(poll_timeout, timeout)
                return True
            timeout()
        else:
            player = self.players[player_id]
            player.access_time = int(runtime.seconds() * 1000)
        return player

    def game_notify(self, args, game_id):
        if args == None:
            del self.games[game_id]
            return False
        if not self.games.has_key(game_id):
            return False
        game = self.games[game_id]
        for player_id in game.get_players():
            if self.players.has_key(player_id):
                self.players[player_id].touch(args)
        d = game.poll(args)
        d.addCallback(self.game_notify, game_id)
        return True

    def create(self, args):
        self.required(args, 'create', 'card', 'sentence', 'owner_id')
        card = int(args['card'][0])
        sentence = args['sentence'][0].decode('utf-8')
        owner_id = int(args['owner_id'][0])

        game = CardstoriesGame(self)
        d = game.create(card, sentence, owner_id)
        def success(game_id):
            self.games[game.get_id()] = game
            args['modified'] = [ game.modified ]
            args['game_id'] = [ game.get_id() ]
            self.game_notify(args, game.get_id())
            return {'game_id': game_id}
        d.addCallback(success)
        return d

    def complete(self, args):
        self.required(args, 'complete', 'owner_id')
        owner_id = int(args['owner_id'][0])
        game_id = self.required_game_id(args)
        d = self.game_method(game_id, 'complete', owner_id)
        def success(value):
            self.games[game_id].destroy()
            return value
        d.addCallback(success)
        return d

    def game(self, args):
        self.required(args, 'game')
        game_id = self.required_game_id(args)
        if args.has_key('player_id'):
            player_id = int(args['player_id'][0])
        else:
            player_id = None
        if self.games.has_key(game_id):
            return self.games[game_id].game(player_id)
        else:
            game = CardstoriesGame(self, game_id)
            d = game.game(player_id)
            def destroy(game_info):
                game.destroy()
                return game_info
            d.addCallback(destroy)
            return d

    def game_proxy(self, args):
        game_id = self.required_game_id(args)
        if not self.games.has_key(game_id):
            raise UserWarning, 'game_id=%s does not exist' % args['game_id']
        return getattr(self.games[game_id], args['action'][0])(args)

    def game_method(self, game_id, action, *args, **kwargs):
        if not self.games.has_key(game_id):
            raise UserWarning, 'game_id=%s does not exist' % args['game_id']
        return getattr(self.games[game_id], action)(*args, **kwargs)

    def participate(self, args):
        self.required(args, 'participate', 'player_id')
        player_id = int(args['player_id'][0])
        game_id = self.required_game_id(args)
        return self.game_method(game_id, args['action'][0], player_id)

    def player2game(self, args):
        self.required(args, 'player2game', 'player_id')
        player_id = int(args['player_id'][0])
        game_id = self.required_game_id(args)
        return self.game_method(game_id, args['action'][0], player_id)

    def pick(self, args):
        self.required(args, 'pick', 'player_id', 'card')
        player_id = int(args['player_id'][0])
        card = int(args['card'][0])
        game_id = self.required_game_id(args)
        return self.game_method(game_id, args['action'][0], player_id, card)

    def vote(self, args):
        self.required(args, 'vote', 'player_id', 'card')
        player_id = int(args['player_id'][0])
        card = int(args['card'][0])
        game_id = self.required_game_id(args)
        return self.game_method(game_id, args['action'][0], player_id, card)

    def voting(self, args):
        self.required(args, 'voting', 'owner_id')
        owner_id = int(args['owner_id'][0])
        game_id = self.required_game_id(args)
        return self.game_method(game_id, args['action'][0], owner_id)

    def invite(self, args):
        self.required(args, 'invite')
        if args.has_key('player_id'):
          player_ids = args['player_id']
        else:
          player_ids = []

        game_id = self.required_game_id(args)
        return self.game_method(game_id, args['action'][0], player_ids)

    @defer.inlineCallbacks
    def lobby(self, args):
        self.required(args, 'lobby', 'player_id', 'in_progress')
        if args['in_progress'][0] == 'true':
            complete = 'state != "complete" AND state != "canceled"'
        else:
            complete = 'state = "complete"'
        order = " ORDER BY created DESC"
        if args.has_key('my') and args['my'][0] == 'true':
            player_id = args['player_id'][0]
            modified = self.get_or_create_player(player_id).get_modified()
            sql =  ""
            sql += " SELECT id, sentence, state, owner_id = player_id, created FROM games, player2game WHERE player2game.player_id = ? AND " + complete + " AND games.id = player2game.game_id"
            sql += " UNION "
            sql += " SELECT id, sentence, state, owner_id = player_id, created FROM games, invitations WHERE invitations.player_id = ? AND " + complete + " AND games.id = invitations.game_id"
            sql += order
            games = yield self.db.runQuery(sql, [ player_id, player_id ])
        else:
            modified = 0
            sql = "SELECT id, sentence, state, owner_id = ?, created FROM games WHERE " + complete
            sql += order
            games = yield self.db.runQuery(sql, [ args['player_id'][0] ])
        sql = "SELECT id, win FROM games, player2game WHERE player2game.player_id = ? AND " + complete + " AND games.id = player2game.game_id"
        rows = yield self.db.runQuery(sql, [ args['player_id'][0] ])
        wins = {}
        for row in rows:
            wins[row[0]] = row[1]
        defer.returnValue({'modified': modified,
                           'games': games,
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

class SSLContextFactory:

    def __init__(self, settings):
        self.pem_file = settings['ssl-pem']

    def getContext(self):
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file(self.pem_file)
        ctx.use_privatekey_file(self.pem_file)
        return ctx
