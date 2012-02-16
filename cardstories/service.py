# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Loic Dachary <loic@dachary.org>
# Copyright (C) 2011-2012 Farsides <contact@farsides.com>
#
# Authors:
#          Loic Dachary <loic@dachary.org>
#          Matjaz Gregoric <mtyaka@gmail.com>
#          Xavier Antoviaque <xavier@antoviaque.org>
#          Adolfo R. Brandes <arbrandes@gmail.com>
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
import os, traceback

from twisted.python import failure, runtime
from twisted.application import service
from twisted.internet import reactor, defer
from twisted.enterprise import adbapi
from twisted.python import log

from cardstories.game import CardstoriesGame
from cardstories.helpers import Observable
from cardstories.exceptions import CardstoriesWarning, CardstoriesException

#from OpenSSL import SSL

import sqlite3

from cardstories.poll import Pollable
from cardstories.auth import Auth


class CardstoriesPlayer(Pollable):

    def __init__(self, service, id):
        self.service = service
        self.settings = service.settings
        self.id = id
        Pollable.__init__(self, self.settings.get('poll-timeout', 30))

    def touch(self, args):
        args['player_id'] = [self.id]
        return Pollable.touch(self, args)


class CardstoriesServiceConnector(object):
    """
    Standard methods for plugins who wish to make requests to the service
    """

    def __init__(self, service):
        self.service = service

    @defer.inlineCallbacks
    def get_game_by_id(self, game_id, player_id=None):
        """
        Returns the current game state corresponding to the provided game_id
        If player_id is provided, the request will be processed as if the corresponding
        player had requested it
        """

        args = {'action': ['state'],
                'type': ['game'],
                'modified': [0],
                'game_id': [game_id]}
        if player_id:
            args['player_id'] = [player_id]

        game, players_ids = yield self.service.handle([], args)
        players_ids = [ int(x['id']) for x in game['players'] ]

        defer.returnValue([game, players_ids])

    @defer.inlineCallbacks
    def get_players_by_game_id(self, game_id):
        """
        Get the players currently playing the game game_id
        """

        game, players_ids = yield self.get_game_by_id(game_id)

        defer.returnValue(players_ids)

    def get_game_id_from_args(self, args):
        """
        Retreives the integer value of the current game, based on the arguments provided
        for the call to the webservice
        Consistently return None if no game_id is provided.
        """

        if 'game_id' in args and args['game_id'][0] and args['game_id'][0] != 'undefined':
            game_id = int(args['game_id'][0])
        else:
            game_id = None

        return game_id


class CardstoriesService(service.Service, Observable):

    ACTIONS_GAME = ('participate', 'voting', 'pick', 'vote', 'complete', 'invite', 'set_countdown')
    ACTIONS = ACTIONS_GAME + ('create', 'poll', 'state', 'player_info', 'remove_tab')

    def __init__(self, settings):
        self.settings = settings
        self.games = {}
        self.players = {}
        self.observers = []
        self.pollable_plugins = []
        self.auth = Auth() # to be overriden by an auth plugin (contains unimplemented interfaces)

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
        c.execute(
            "CREATE TABLE tabs ( "
            "  player_id INTEGER, "
            "  game_id INTEGER, "
            "  created DATETIME "
            "); ")
        c.execute(
            "CREATE UNIQUE INDEX tabs_idx ON tabs (player_id, game_id); "
            )
        c.execute(
            "CREATE TABLE players ( "
            "  id INTEGER PRIMARY KEY, "
            "  score BIGINTEGER, "
            "  levelups INTEGER "
            "); ")
        c.execute(
            "CREATE TABLE player_cards ( "
            "  id INTEGER PRIMARY KEY, "
            "  player_id INTEGER, "
            "  card INTEGER, "
            "  UNIQUE (\"player_id\", \"card\") "
            "); ")

    def load(self, c):
        c.execute("SELECT id, sentence FROM games WHERE state != 'complete' AND state != 'canceled'")
        for (id, sentence) in c.fetchall():
            game = CardstoriesGame(self, id)
            game.load(c)

            # Notify listeners of the game, but also inform them that this is done
            # during startup, for example to allow plugins to ignore such "reloaded" games
            # Note that the db is not accessible during that stage
            self.game_init(game, sentence, server_starting=True)

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
                return defer.succeed({'game_id': [game_id],
                                      'modified': [int(runtime.seconds() * 1000)]})
            else:
                deferreds.append(self.games[game_id].poll(args))

        if 'tabs' in args['type']:
            deferreds.append(self.poll_tabs(args))

        if 'lobby' in args['type']:
            deferreds.append(self.poll_player(args))

        for plugin in self.pollable_plugins:
            if plugin.name() in args['type']:
                deferreds.append(plugin.poll(args))

        d = defer.DeferredList(deferreds, fireOnOneCallback=True)
        d.addCallback(lambda x: x[0])

        # Allow listeners to monitor when polls are started or ended
        if deferreds:
            if 'player_id' in args:
                player_id = args['player_id'][0]
            else:
                player_id = None
            self.notify({'type': 'poll_start',
                         'player_id': player_id})

            def on_poll_end(return_value):
                self.notify({'type': 'poll_end',
                             'player_id': player_id})
                return return_value
            d.addCallback(on_poll_end)

        return d

    def poll_tabs(self, args):
        """
        Gets the games that should be monitored as tabs by the current user,
        and returns a deferred list of polled games.
        """
        # We need to nest one deferred inside another, because we are dealing with
        # two async operations: fetching game ids from the DB, and waiting in a poll.
        # The outer callback fires when the game ids are fetched from the DB, while the
        # inner one fires when one of the polled games has been modified, causing poll to return.
        outer_deferred = self.get_tab_game_ids(args)
        def outer_callback(result):
            game_deferreds = []
            for game_id in result:
                if self.games.has_key(game_id):
                    game_deferreds.append(self.games[game_id].poll(args))
            def inner_callback(result):
                # Make the tabs poll always return just the arguments with updated timestamp.
                args['modified'] = result[0]['modified']
                return args
            inner_deferred = defer.DeferredList(game_deferreds, fireOnOneCallback=True)
            inner_deferred.addCallback(inner_callback)
            return inner_deferred
        outer_deferred.addCallback(outer_callback)
        return outer_deferred

    def tabsInteraction(self, transaction, player_id, game_id):
        transaction.execute('SELECT game_id from tabs WHERE player_id = ? ORDER BY created ASC', [player_id])
        rows = transaction.fetchall()
        game_ids = [row[0] for row in rows]
        if game_id and game_id not in game_ids:
            sql = "INSERT INTO tabs (player_id, game_id, created) VALUES (?, ?, datetime('now'))"
            transaction.execute(sql, [player_id, game_id])
            game_ids.append(game_id)
        return game_ids

    @defer.inlineCallbacks
    def get_tab_game_ids(self, args):
        """
        Expects 'player_id' and optionally a 'game_id' in the args.
        If there is a 'game_id' in the args and that game_id is not yet associated
        with the player in the tabs table, it associates the game_id with player_id in
        the table.
        Returns a list of game_ids associated with the player in the tabs table.
        """
        player_id = args['player_id'][0]
        game_id = args.has_key('game_id') and args['game_id'][0]
        try:
            game_id = int(game_id)
        except:
            game_id = None
        if player_id:
            game_ids = yield self.db.runInteraction(self.tabsInteraction, player_id, game_id)
        else:
            game_ids = []
        defer.returnValue(game_ids)

    def remove_tab(self, args):
        """
        Processes requests to remove game from player's list of tabs.
        Expects 'player_id' and 'game_id' to be present in the args.
        Removes association between player and game from the tabs table.
        """
        self.required(args, 'remove_tab', 'player_id')
        game_id = self.required_game_id(args)
        player_id = int(args['player_id'][0])
        d = self.db.runQuery('DELETE FROM tabs WHERE player_id = ? AND game_id = ?', [ player_id, game_id ])
        def success(result):
            return {'type': 'remove_tab'}
        d.addCallback(success)
        return d

    @defer.inlineCallbacks
    def update_players_info(self, players_info, players_id_list):
        '''Add new player ids as key to players_info dict, from players_list'''

        for player_id in players_id_list:
            if player_id not in players_info:
                info = {}
                try:
                    info['name'] = yield self.auth.get_player_name(player_id)
                    info['avatar_url'] = yield self.auth.get_player_avatar_url(player_id)
                except Exception as e:
                    raise CardstoriesException('Failed fetching player data (player_id=%s): %s' % (player_id, e))
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

        if 'tabs' in args['type']:
            game_ids = yield self.get_tab_game_ids(args)
            tabs = {'type': 'tabs', 'games': []}
            player_id = args.get('player_id')
            max_modified = 0
            for game_id in game_ids:
                game_args = {'action': 'game', 'game_id': [game_id]}
                if player_id: game_args['player_id'] = player_id
                game, players_id_list = yield self.game(game_args)
                tabs['games'].append(game)
                if game['modified'] > max_modified:
                    max_modified = game['modified']
            tabs['modified'] = max_modified
            states.append(tabs)

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
                state['modified'] = plugin.get_modified(args=args)
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

            poll_timeout = self.settings.get('poll-timeout', 30)

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

    @defer.inlineCallbacks
    def game_init(self, game, sentence, previous_game_id=None, server_starting=False):
        self.games[game.get_id()] = game
        args = {
            'type': 'init',
            'modified': [0],
            'game_id': [game.get_id()],
            'sentence': [sentence],
            'previous_game_id': previous_game_id,
            'server_starting': server_starting}

        args = yield game.wait(args)
        yield self.game_notify(args, game.get_id())

    @defer.inlineCallbacks
    def create(self, args):
        self.required(args, 'create', 'card', 'sentence', 'owner_id')
        card = int(args['card'][0])
        sentence = args['sentence'][0].decode('utf-8')
        owner_id = int(args['owner_id'][0])

        # Keep track of consecutive games
        if 'previous_game_id' in args:
            previous_game_id = args['previous_game_id'][0]
        else:
            previous_game_id = None

        game = CardstoriesGame(self)
        game_id = yield game.create(card, sentence, owner_id)

        yield self.game_init(game, sentence, previous_game_id=previous_game_id)

        defer.returnValue({'game_id': game_id})

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
            raise CardstoriesWarning('GAME_NOT_LOADED', {'game_id': game_id})
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
                    error = reason.value
                    log.err(reason)
                    if reason.type is CardstoriesWarning:
                        return {'error': {'code': error.code, 'data': error.data}}
                    else:
                        tb = error.args[0]
                        tb += '\n\n'
                        tb += ''.join(traceback.format_tb(reason.getTracebackObject()))
                        return {'error': {'code': 'PANIC', 'data': tb}}
                d.addErrback(error)
                return d
            else:
                raise CardstoriesException, 'Unknown action: %s' % action
        except CardstoriesWarning as e:
            log.err(e)
            return defer.succeed({'error': {'code': e.code, 'data': e.data}})
        except Exception as e:
            log.err(e)
            tb = traceback.format_exc()
            return defer.succeed({'error': {'code': 'PANIC', 'data': tb}})

    @staticmethod
    def required(args, action, *keys):
        for key in keys:
            if not args.has_key(key):
                raise CardstoriesException, "Action '%s' requires argument '%s', but it was missing." % (action, key)
        return True

    @staticmethod
    def required_game_id(args):
        CardstoriesService.required(args, args['action'][0], 'game_id')
        game_id = int(args['game_id'][0])
        if game_id <= 0:
            raise CardstoriesException, 'game_id cannot be negative: %d' % args['game_id']
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
