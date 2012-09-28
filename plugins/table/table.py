# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Farsides <contact@farsides.com>
#
# Authors:
#          Xavier Antoviaque <xavier@antoviaque.org>
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

# Imports ##################################################################

import os
from twisted.internet import defer, reactor
from twisted.python import log

from cardstories.poll import Pollable
from cardstories.service import CardstoriesServiceConnector
from cardstories.game import CardstoriesGame


# Classes ##################################################################

class Plugin(Pollable, CardstoriesServiceConnector):
    """
    The table plugin keeps track of group of players playing a series of games together.

    It allows to find available games to join, and let the players easily replay with
    the same players, automatically assigning the game master role to each player in turn.
    """

    def __init__(self, service, plugins):
        # Storage for tables
        self.tables = []

        # Store the relationship between tables and games
        self.game2table = {}

        # Depends on the activity plugin (to know when players are online)
        for plugin in plugins:
            if plugin.name() == 'activity':
                self.activity_plugin = plugin
        assert self.activity_plugin

        # Register a function to know when players go online/offline
        self.activity_plugin.listen().addCallback(self.on_activity_notification)

        # Register a function to listen to the game events.
        self.service = service
        self.service.listen().addCallback(self.on_service_notification)

        # Implement the path conventions
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], self.name())
        self.libdir = os.path.join(self.service.settings['plugins-libdir'], self.name())

        # Initialize the pollable using the recommended timeout.
        Pollable.__init__(self, self.service.settings.get('poll-timeout', 30))

    def name(self):
        """
        Method required by all plugins to inspect the plugin's name.
        """
        return 'table'

    def on_service_notification(self, changes):
        """
        If a 'change' notification is received of the 'init' type, call the
        appropriate method and reinsert our listen() callback so we get called
        again later, when there's a new event.
        """

        d = defer.succeed(True)

        if changes != None:
            if changes['type'] == 'change':
                details = changes['details']
                if details['type'] == 'create':
                    d = self.on_new_game(changes['game'], details)
                elif details['type'] == 'set_sentence':
                    d = self.on_game_sentence_set(changes['game'], details)
                elif details['type'] == 'complete':
                    d = self.on_game_complete(changes['game'], details)

        self.service.listen().addCallback(self.on_service_notification)
        return d

    @defer.inlineCallbacks
    def on_new_game(self, game, details):
        """
        Called every time a new game is created

        Keep track of relationships between games and tables:
        - Brand new games create a new table
        - Games based on previous games are registered on the existing table
        """

        previous_game_id = None
        previous_game = None

        if 'previous_game_id' in details \
                and details['previous_game_id'] \
                and details['previous_game_id'] != 'undefined':
            previous_game_id = int(details['previous_game_id'])
            previous_game, players_ids = yield self.get_game_by_id(previous_game_id)

        if not previous_game_id \
                or previous_game_id not in self.game2table:
            # Register new table
            table = self.create_new_table()
            log.msg('New table created for game %d' % game.id)
        else:
            # Register new game in existing table
            table = self.game2table[previous_game_id]
            log.msg('Game %d added to existing table (game_ids = %s)' % (game.id, table.games_ids))

        self.game2table[game.id] = table
        table.register_new_game(game)

        self.touch({})

        defer.returnValue(True)

    def create_new_table(self):
        """Creates a new table and associates it with this plugin."""
        table = Table(self)
        self.tables.append(table)
        return table

    def on_game_sentence_set(self, game, details):
        """
        Invoked when one of the gamesgets its sentence set, moving into 'invitation' state.
        Delegates to the game's table, if it exists.
        """

        table = self.game2table.get(game.id)
        if table:
            table.on_game_sentence_set(game.id)

    def on_game_complete(self, game, details):
        """
        Invoked when one of the games is completed.
        Delegates to the game's table, if it exists.
        """

        table = self.game2table.get(game.id)
        if table:
            table.on_game_complete(game.id)

    def on_activity_notification(self, changes):
        """
        Called every time the activity plugin notifies of an event,
        such as player connection/disconnection

        Route the notifications we're interested in to the appropriate method.
        """

        d = defer.succeed(True)

        if changes != None and changes['type'] == 'player_disconnecting':
            d = self.on_player_disconnecting(int(changes['player_id']))

        self.activity_plugin.listen().addCallback(self.on_activity_notification)
        return d

    @defer.inlineCallbacks
    def on_player_disconnecting(self, player_id):
        """
        Called every time a player disconnects.
        
        Delete empty tables to avoid memory leak
        """

        for table in self.tables[:]: # self.tables can be altered
            yield table.on_player_disconnecting(player_id)

            active_players, inactive_players = yield table.get_active_players()
            if len(active_players) < 1:
                self.delete_table(table)
                log.msg('Table deleted (game_ids = %s)' % table.games_ids)

        defer.returnValue(True)

    def delete_table(self, table):
        """
        Deletes a table and all its references, freeing the memory
        """

        self.tables.remove(table)
        for game_id, game_table in self.game2table.items():
            if table == game_table:
                table.stop_timer(table.next_game_timer)
                del self.game2table[game_id]

    def poll(self, args):
        """
        Handles poll requests
        
        Redefined from Pollable.poll() to delegate to the relevant table when available
        Otherwise monitors new game/table availability.
        """

        game_id = self.get_game_id_from_args(args)

        # Delegate poll() to table when it exists
        if game_id in self.game2table:
            table = self.game2table[game_id]
            return table.poll(args)

        # The current game isn't in a table, or no game is displayed at all.
        # The poll returns when a new game becomes available in any table
        else:
            return Pollable.poll(self, args)

    @defer.inlineCallbacks
    def state(self, args):
        """
        Returns the current table state

        Delegated to the appropriate table (which can be either a table a player has
        already joined, or an available table to join) when we've got one,
        Otherwise tell the player to create a game/table himself
        """

        player_id = int(args['player_id'][0])
        game_id = self.get_game_id_from_args(args)

        if game_id and game_id in self.game2table:
            table = self.game2table[game_id]
        else:
            # No table for that game, try to find a new table for the player
            table = yield self.get_available_table()

        if table:
            # Delegate state() answering to table
            result = yield table.state(args)
        else:
            # Tell the player to create a new game (and thus a new table)
            result = [{'game_id': game_id, 'next_game_id': None, 'next_owner_id': player_id}, [player_id]]

        defer.returnValue(result)

    def get_modified(self, args=None):
        """
        Returns last poll object modification
        
        Redefined from Pollable.get_modified() to delegate to the relevant table when available
        """

        game_id = self.get_game_id_from_args(args)

        if game_id in self.game2table:
            table = self.game2table[game_id]
            return table.get_modified()
        else:
            return Pollable.get_modified(self)

    @defer.inlineCallbacks
    def get_available_table(self):
        """
        Returns the active table with the maximum number of players
        which isn't full (ie try to concentrate players on a few tables)
        """

        best_table = None
        max_players = 0

        for table in self.tables:
            game = yield table.get_current_game()
            if game['state'] in ['create', 'invitation']:
                active_players, inactive_players = yield table.get_active_players()
                if len(active_players) > max_players \
                        and len(active_players) + len(inactive_players) < CardstoriesGame.NPLAYERS:
                    best_table = table
                    max_players = active_players

        defer.returnValue(best_table)

    @defer.inlineCallbacks
    def postprocess(self, result, request):
        """
        Hooks into the response to add table specific information to any
        'tabs' type state request.
        This makes it possible for the tab JS plugin to highlight tabs based
        on the table next owner/next game info.
        """

        if type(result) is list:
            for state in result:
                if type(state) is dict:
                    if state.get('type') == 'tabs':
                        for game in state['games']:
                            args = request.args.copy()
                            args['game_id'] = [game['id']]
                            table_state, player_ids = yield self.state(args)
                            game['next_owner_id'] = table_state['next_owner_id']
                            game['next_game_id'] = table_state['next_game_id']
        defer.returnValue(result)


class Table(Pollable, CardstoriesServiceConnector):
    """
    Describes a single table
    """

    NEXT_GAME_TIMEOUT = 60

    def __init__(self, table_plugin):
        self.table_plugin = table_plugin
        self.activity_plugin = self.table_plugin.activity_plugin
        self.service = self.table_plugin.service
        # A list of game IDs of all games ever played in this table,
        # in chronological order (oldest game comes first in the list,
        # while the last game in the list is the most recent, "current" game
        # of the table.
        self.games_ids = []
        # A list of new games that were created as next_games of the table, but didn't
        # yet reach the 'invitation' state. The first pending game that reaches
        # 'invitation' state is promoted to be the next_game, while any other
        # pending game is spun off into its own, brand new table.
        self.pending_games = []
        # A list of unique IDs of all users that were chosen to be the next_owner
        # at some point (even if they failed to create the next game),
        # in reverse chronological order (owner that was the most recent next_owner
        # comes first in the list). Keeping track of them for the sole purpose of
        # being able to cycle between next owners when the time to update next_owner_id comes.
        self.chosen_owners_ids = []
        # The ID of the player who is currently chosen as the next owner.
        self.next_owner_id = None
        # Timer that keeps track of how long it takes the next_owner to create the next
        # game and make it "playable" (move it into invitation state). If the next owner
        # doesn't manage to do that in under NEXT_GAME_TIMEOUT seconds, another next_owner
        # is chosen instead.
        self.next_game_timer = None
        # When current game is completed, self.next_game_promoted is set to False until one
        # of the pending games that get created is promoted to be the new current game.
        self.next_game_promoted = None
        # If self.next_owner_id is currently (asynchonously) being updated,
        # self.next_owner_deferred is set to a deferred that will fire once the update_next_owner_id
        # operation completes. Set to None when no next_owner update is in progress.
        self._next_owner_deferred = None
        # update_next_owner_id is asynchronous because its waiting for results of get_active_players
        # operation. We store this as an attribute of the table, so that we are able to cancel the
        # deferred attached to the get_active_players result and start a new one in case a new
        # update_next_owner_id request is made before the one already in progress completes.
        # This is an implementation detail.
        self._active_players_deferred = None

        Pollable.__init__(self, self.service.settings.get('poll - timeout', 30))

    def register_new_game(self, game):
        """
        Registers the latest game for the table when it is created.
        """

        # If this is the first game, make it the table's current game, otherwise keep track of it
        # in the pending_games array. Pending games will be promoted to the current game
        # status only after they reach the 'invitation' state.
        if len(self.games_ids) == 0:
            self.promote_game(game.id)
        else:
            self.pending_games.append(game)

        self.register_chosen_owner(game.owner_id)

        self.touch({})

    def register_chosen_owner(self, owner_id):
        # Don't add a owner_id twice
        self.chosen_owners_ids = filter(lambda x: x != owner_id, self.chosen_owners_ids)
        self.chosen_owners_ids.insert(0, owner_id)

    def start_timer(self, timeout, callback, *args):
        timer = reactor.callLater(timeout, callback, *args)
        return timer

    def stop_timer(self, timer):
        if timer and timer.active():
            timer.cancel()

    def on_game_sentence_set(self, game_id):
        """
        When one of the games of the table moves into 'invitation' state,
        promote to be the next_game, if none has been promoted yet for this game cycle,
        otherwise if it was one of the pending games that entered 'invitation' state,
        detach it from this table.
        """

        # We already promoted our next game, so if the game who had its
        # sentence set is still pending, detach it from this table.
        if self.next_game_promoted:
            for pending_game in self.pending_games:
                if pending_game.id == game_id:
                    self.detach_game(pending_game)
        # We didn't promote a game yet, looks like we got a suitable candidate now!
        else:
            if game_id not in self.games_ids:
                self.promote_game(game_id)

    def on_game_complete(self, game_id):
        """
        When the current game of the table reaches 'complete' state,
        All games still pending from the previous cycle are detached.
        """

        if game_id == self.games_ids[-1]:
            for pending_game in self.pending_games:
                self.detach_game(pending_game)
            self.next_game_promoted = False

    def detach_game(self, game):
        """
        Spins the game off into its own table, completely detaching
        it from this table.
        """

        self.pending_games = filter(lambda g: g.id != game.id, self.pending_games)
        table = self.table_plugin.create_new_table()
        table.register_new_game(game)
        self.table_plugin.game2table[game.id] = table

    def promote_game(self, game_id):
        """
        Promotes the game from the pending state to be the next game of this table,
        spinning other pending games off into their own tables.
        """

        self.pending_games = filter(lambda g: g.id != game_id, self.pending_games)
        self.games_ids.append(game_id)
        self.next_game_promoted = True
        self.stop_timer(self.next_game_timer)
        self.next_owner_id = None

        # Let clients know that the next game is available
        self.touch({})

    @defer.inlineCallbacks
    def get_current_game(self):
        """
        Returns the game object of the active game for this table,
        (the last game created on this table)
        """

        current_game_id = self.get_current_game_id()
        game_res = yield self.get_game_by_id(current_game_id)
        game, players_ids = game_res

        defer.returnValue(game)

    def get_current_game_id(self):
        """
        Returns the game_id of the active game for this table
        """

        return self.games_ids[-1]

    @defer.inlineCallbacks
    def state(self, args):
        """
        Gives the state of the current table

        Format: {"game_id": 2231,       # The current game the player is in (ie the one provided in the WS request)
                 "next_game_id": null,  # The currently active game for this table (if different from game_id)
                 "next_owner_id": null, # The id of the player who will create the next game
                 "type": "table"}
        """

        player_id = args['player_id'][0]
        player_game_id = self.get_game_id_from_args(args)
        table_game_id = self.get_current_game_id()
        table_game = yield self.get_current_game()

        # Player is asking from another game - this can happen for three reasons:
        # 1) the next game of the table was created and promoted, and player is inquiring about it
        #    from the previous game (in complete state);
        # 2) the next game was created (and joined by the player), but the owner didn't yet set
        #    the card and sentence, so the game is still in pending state, and there is no next game yet;
        # 3) the next game was created (and joined by the player), but the owner didn't set
        #    the card and sentence in time, and another game was promoted to be the next game of the table.
        if player_game_id != table_game_id:
            if len(filter(lambda g: g.id == player_game_id, self.pending_games)):
                # Player is inquring from a pending game. Did we get the next game
                # of the table yet?
                if table_game['state'] == 'complete':
                    # Nope, not yet (bullet 2).
                    next_game_id = None
                    next_owner_id = self.next_owner_id
                else:
                    # Yes, we've got the next game! (bullet 3)
                    next_game_id = table_game_id
                    next_owner_id = table_game['owner_id']
            # Player is either inquiring from the previous game in complete state (bullet 1).
            else:
                next_game_id = table_game_id
                next_owner_id = table_game['owner_id']

        # Player is asking from the current table game.
        # Show him the current next_owner_id and id of the corresponding
        # pending game (if it was already created).
        else:
            if table_game['state'] in ['complete', 'canceled']:
                if self.next_owner_id is None:
                    yield self.update_next_owner_id()

                next_owner_id = self.next_owner_id
                next_game_id = None

                for game in self.pending_games:
                    if game.owner_id == self.next_owner_id:
                        next_game_id = game.id
                        break
            else:
                next_game_id = None
                next_owner_id = self.next_owner_id

        # Player info
        if next_owner_id:
            players_ids = [next_owner_id]
        else:
            players_ids = []

        defer.returnValue([{'game_id': player_game_id,
                            'next_game_id': next_game_id,
                            'next_owner_id': next_owner_id},
                           players_ids])

    @defer.inlineCallbacks
    def get_active_players(self):
        """
        Returns the id of all players participating to the current active game for this table,
        separated in two lists, depending on their online status, and whether or not they have
        a tab with the game corresponding to this table.

        Format: [active_players_ids, inactive_players_ids]
        """

        current_game_id = self.get_current_game_id()
        players_ids = yield self.get_players_by_game_id(current_game_id)

        active_players_ids = []
        inactive_players_ids = []
        for player_id in players_ids:
            if self.activity_plugin.is_player_online(player_id):
                active_players_ids.append(player_id)
            else:
                inactive_players_ids.append(player_id)

        defer.returnValue([active_players_ids, inactive_players_ids])

    def update_next_owner_id(self):
        """
        Chose the next player who will create a game on this table, if necessary.

        Returns the name of the player, and sets the self.owner_id attribute.
        """

        if self._next_owner_deferred is None:
            self._next_owner_deferred = defer.Deferred()

        # If an active_players_deferred is currently running, cancel it and start another one.
        if self._active_players_deferred:
            self._active_players_deferred.cancel()
        self._active_players_deferred = self.get_active_players()

        # Store current value of next_owner_id to be able to compare later.
        previous_next_owner_id = self.next_owner_id

        def success(result):
            active_players_ids, inactive_players_ids = result
            # Filter out all players who already created next games (that are currently pending).
            pending_game_owners_ids = [g.owner_id for g in self.pending_games]
            owner_candidates_ids = [pid for pid in active_players_ids if pid not in pending_game_owners_ids]

            if len(owner_candidates_ids) >= 1:
                # Take the player who was a game owner the longest ago (or never).
                # This is to try to evenly distribute game ownership among players,
                # so that it's not always the same player who gets to be the GM.
                for owner_id in self.chosen_owners_ids:
                    if len(owner_candidates_ids) == 1:
                        break
                    elif owner_id in owner_candidates_ids:
                        owner_candidates_ids.remove(owner_id)

                self.next_owner_id = owner_candidates_ids[0]
                self.register_chosen_owner(self.next_owner_id)

                self.stop_timer(self.next_game_timer)
                self.next_game_timer = self.start_timer(
                    self.NEXT_GAME_TIMEOUT,
                    self.update_next_owner_if_no_game,
                    self.get_current_game_id()
                )


            next_owner_deferred = self._next_owner_deferred
            self._next_owner_deferred = None
            self._active_players_deferred = None

            # Let clients know if the next owner has been chosen.
            if self.next_owner_id != previous_next_owner_id:
                self.touch({})

            # Finally, fire the deferred that the caller of this method is holding on to.
            next_owner_deferred.callback({})

        def error(reason):
            # If the error is result of cancelling the deffered, just ignore it,
            # otherwise let it propagate.
            if not reason.check(defer.CancelledError):
                return reason

        self._active_players_deferred.addCallbacks(success, error)

        return self._next_owner_deferred

    @defer.inlineCallbacks
    def update_next_owner_if_no_game(self, game_id):
        """
        If current game is still `game_id`, discards current next game owner
        (as he hasn't managed to create a new game in time), and chooses another player instead.
        """

        if self.get_current_game_id() == game_id:
            yield self.update_next_owner_id()

    @defer.inlineCallbacks
    def on_player_disconnecting(self, player_id):
        """
        Called every time a player disconnects
        (not necessarily an active player from the current table game)

        Change the next owner when he disconnects
        """
        if self.next_owner_id and self.next_owner_id == player_id:
            yield self.update_next_owner_id()
