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

from twisted.python import failure, runtime
from twisted.application import service
from twisted.internet import reactor, defer
from twisted.enterprise import adbapi

from cardstories.game import CardstoriesGame

#from OpenSSL import SSL

import sqlite3

from cardstories.poll import pollable
from cardstories.auth import Auth

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

    ACTIONS_GAME = ('participate', 'voting', 'pick', 'vote', 'complete', 'invite', 'set_countdown')
    ACTIONS = ACTIONS_GAME + ('create', 'poll', 'state', 'player_info')

    def __init__(self, settings):
        self.settings = settings
        self.games = {}
        self.players = {}
        self.listeners = []
        self.pollable_plugins = []
        self.auth = Auth() # to be overriden by an auth plugin (contains unimplemented interfaces)

    def listen(self):
        d = defer.Deferred()
        self.listeners.append(d)
        return d

    def notify(self, result):
        if hasattr(self, 'notify_running'):
            raise UserWarning, 'recursive call to notify'
        self.notify_running = True
        listeners = self.listeners
        self.listeners = []
        def error(reason):
            reason.printTraceback()
            return True
        d = defer.DeferredList(listeners)
        for listener in listeners:
            listener.addErrback(error)
            listener.callback(result)
        del self.notify_running
        return d

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
        self.db = adbapi.ConnectionPool("sqlite3", database=database, cp_noisy=True, check_same_thread=False)
        self.notify({'type': 'start'})

    @defer.inlineCallbacks
    def stopService(self):
        yield self.notify({'type': 'stop'})
        for game in self.games.values():
            game.destroy()
        for player in self.players.values():
            if player.timer.active():
                player.timer.cancel()
            player.destroy()
        defer.returnValue(None)

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
            "  serial INTEGER PRIMARY KEY, "
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
        c.execute("SELECT id, sentence FROM games WHERE state != 'complete' AND state != 'canceled'")
        for (id, sentence) in c.fetchall():
            game = CardstoriesGame(self, id)
            game.load(c)
            self.game_init(game, sentence)

    def poll(self, args):
        self.required(args, 'poll', 'type', 'modified')
        deferreds = []
        if 'game' in args['type']:
            game_id = self.required_game_id(args)
            if not self.games.has_key(game_id):
                # This means the game has been deleted from memory - probably because
                # it has been completed. The client doesn't seem to be aware of this yet,
                # so just return the poll immediately to let the client know the state
                # has changed.
                return defer.succeed({ 'game_id': [game_id],
                                       'modified': [int(runtime.seconds() * 1000)] })
            else:
                deferreds.append(self.games[game_id].poll(args))
        if 'lobby' in args['type']:
            deferreds.append(self.poll_player(args))
        for plugin in self.pollable_plugins:
            if plugin.name() in args['type']:
                deferreds.append(plugin.poll(args))
        d = defer.DeferredList(deferreds, fireOnOneCallback=True)
        d.addCallback(lambda x: x[0])
        return d

    @defer.inlineCallbacks
    def update_players_info(self, players_info, players_id_list):
        '''Add new player ids as key to players_info dict, from players_list'''

        for player_id in players_id_list:
            if player_id not in players_info:
                info = {}
                info['name'] = yield self.auth.get_player_name(player_id)
                info['avatar_url'] = yield self.auth.get_player_avatar_url(player_id)
                players_info[str(player_id)] = info

        defer.returnValue(players_info)

    @defer.inlineCallbacks
    def player_info(self, args):
        '''Process requests to retreive player_info for a player_id'''

        self.required(args, 'player_info', 'player_id')

        players_info = {'type': 'players_info'}
        yield self.update_players_info(players_info, args['player_id'])
        defer.returnValue([players_info])

    @defer.inlineCallbacks
    def state(self, args):
        self.required(args, 'state', 'type', 'modified')
        states = []
        players_info = {'type': 'players_info'} # Keep track of all players being referenced

        if 'game' in args['type']:
            game_args = {'action': 'game',
                         'game_id': args['game_id'] }
            if args.has_key('player_id'):
                game_args['player_id'] = args['player_id']

            game, players_id_list = yield self.game(game_args)
            game['type'] = 'game'
            states.append(game)
            yield self.update_players_info(players_info, players_id_list)

        if 'lobby' in args['type']:
            lobby, players_id_list = yield self.lobby({'action': 'lobby',
                                      'in_progress': args['in_progress'],
                                      'my': args.get('my', ['true']),
                                      'player_id': args['player_id']})
            lobby['type'] = 'lobby'
            states.append(lobby)
            yield self.update_players_info(players_info, players_id_list)

        for plugin in self.pollable_plugins:
            if plugin.name() in args['type']:
                state, players_id_list = yield plugin.state(args)
                state['type'] = plugin.name()
                state['modified'] = plugin.get_modified()
                states.append(state)
                yield self.update_players_info(players_info, players_id_list)

        states.append(players_info)
        defer.returnValue(states)

    def poll_player(self, args):
        player_id = int(args['player_id'][0])
        player = self.get_or_create_player(player_id)
        return player.poll(args)

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
            @defer.inlineCallbacks
            def timeout():
                now = int(runtime.seconds() * 1000)
                if not self.players.has_key(player_id):
                    defer.returnValue(False)
                player = self.players[player_id]
                if now - player.access_time > (poll_timeout * 2 * 1000):
                    yield player.touch({'delete': [now]})
                    del self.players[player_id]
                else:
                    player.timer = reactor.callLater(poll_timeout, timeout)
                defer.returnValue(True)
            timeout()
        else:
            player = self.players[player_id]
            player.access_time = int(runtime.seconds() * 1000)
        return player

    @defer.inlineCallbacks
    def game_notify(self, args, game_id):
        if args == None:
            yield self.notify({'type': 'delete', 'game': self.games[game_id], 'details': args})
            del self.games[game_id]
            defer.returnValue(False)
        if not self.games.has_key(game_id):
            defer.returnValue(False)
        game = self.games[game_id]
        modified = game.get_modified()
        yield self.notify({'type': 'change', 'game': game, 'details': args})
        for player_id in game.get_players():
            if self.players.has_key(player_id):
                yield self.players[player_id].touch(args)
        #
        # the functions being notified must not change the game state
        # because the behavior in this case is undefined
        #
        assert game.get_modified() == modified
        d = game.wait(args)
        d.addCallback(self.game_notify, game_id)
        defer.returnValue(True)

    def game_init(self, game, sentence):
        self.games[game.get_id()] = game
        args = {
            'type': 'init',
            'modified': [0],
            'game_id': [game.get_id()],
            'sentence': [sentence]}
        d = game.wait(args)
        d.addCallback(self.game_notify, game.get_id())

    def create(self, args):
        self.required(args, 'create', 'card', 'sentence', 'owner_id')
        card = int(args['card'][0])
        sentence = args['sentence'][0].decode('utf-8')
        owner_id = int(args['owner_id'][0])

        game = CardstoriesGame(self)
        d = game.create(card, sentence, owner_id)
        def success(game_id):
            self.game_init(game, sentence)
            return {'game_id': game_id}
        d.addCallback(success)
        return d

    def complete(self, args):
        self.required(args, 'complete', 'owner_id')
        owner_id = int(args['owner_id'][0])
        game_id = self.required_game_id(args)
        d = self.game_method(game_id, 'complete', owner_id)
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

    def game_method(self, game_id, action, *args, **kwargs):
        if not self.games.has_key(game_id):
            raise UserWarning, 'game_id=%s does not exist' % str(game_id)
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

    @defer.inlineCallbacks
    def invite(self, args):
        self.required(args, 'invite')
        if args.has_key('invited_email'):
            player_ids = yield self.auth.get_players_ids(args['invited_email'], create=True)
        else:
            player_ids = []

        if args.has_key('player_id'):
            player_ids += args['player_id']

        game_id = self.required_game_id(args)
        result = yield self.game_method(game_id, args['action'][0], player_ids)
        defer.returnValue(result)

    def set_countdown(self, args):
        self.required(args, 'set_countdown', 'duration')
        duration = int(args['duration'][0])
        game_id = self.required_game_id(args)
        return self.game_method(game_id, args['action'][0], duration)

    @defer.inlineCallbacks
    def lobby(self, args):
        self.required(args, 'lobby', 'player_id', 'in_progress')

        player_id = args['player_id'][0]
        players_info = [player_id] # Only the current player is referenced by lobby

        if args['in_progress'][0] == 'true':
            complete = 'state != "complete" AND state != "canceled"'
        else:
            complete = 'state = "complete"'
        order = " ORDER BY created DESC"

        if args.has_key('my') and args['my'][0] == 'true':
            modified = self.get_or_create_player(player_id).get_modified()
            sql = ""
            sql += " SELECT id, sentence, state, owner_id = player_id, created FROM games, player2game WHERE player2game.player_id = ? AND " + complete + " AND games.id = player2game.game_id"
            sql += " UNION "
            sql += " SELECT id, sentence, state, owner_id = player_id, created FROM games, invitations WHERE invitations.player_id = ? AND " + complete + " AND games.id = invitations.game_id"
            sql += order
            games = yield self.db.runQuery(sql, [ player_id, player_id ])
        else:
            modified = 0
            sql = "SELECT id, sentence, state, owner_id = ?, created FROM games WHERE " + complete
            sql += order
            games = yield self.db.runQuery(sql, [ player_id ])

        sql = "SELECT id, win FROM games, player2game WHERE player2game.player_id = ? AND " + complete + " AND games.id = player2game.game_id"
        rows = yield self.db.runQuery(sql, [ player_id ])
        wins = {}
        for row in rows:
            wins[row[0]] = row[1]
        defer.returnValue([{'modified': modified,
                           'games': games,
                           'win': wins},
                           players_info])

    def handle(self, result, args):
        if not args.has_key('action'):
            return defer.succeed(result)
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
            failure.Failure().printTraceback()
            return defer.succeed({'error': e.args[0]})

    @staticmethod
    def required(args, method, *keys):
        for key in keys:
            if not args.has_key(key):
                raise UserWarning, '%s must be given a %s value' % (method, key)
        return True

    @staticmethod
    def required_game_id(args):
        if not args.has_key('game_id'):
            raise UserWarning, '%s must be given a game_id value' % args['action'][0]
        game_id = int(args['game_id'][0])
        if game_id <= 0:
            raise UserWarning, 'game_id=%s must be an integer > 0' % args['game_id']
        return game_id

#class SSLContextFactory:
#
#    def __init__(self, settings):
#        self.pem_file = settings['ssl-pem']
#
#    def getContext(self):
#        ctx = SSL.Context(SSL.SSLv23_METHOD)
#        ctx.use_certificate_file(self.pem_file)
#        ctx.use_privatekey_file(self.pem_file)
#        return ctx
