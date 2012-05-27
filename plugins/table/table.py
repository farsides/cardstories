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
from twisted.internet import defer
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
            elif changes['type'] == 'tab_removed':
                d = self.on_tab_closed(changes['player_id'], changes['game_id'])

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
                or previous_game_id not in self.game2table \
                or (previous_game['state'] != 'canceled' and \
                    previous_game['state'] != 'complete'): # only add new game to a table when previous game is over
            # Register new table
            table = Table(self)
            self.tables.append(table)
            log.msg('New table created for game %d' % game.id)
        else:
            # Register new game in existing table
            table = self.game2table[previous_game_id]
            log.msg('Game %d added to existing table (game_ids = %s)' % (game.id, table.games_ids))

        self.game2table[game.id] = table
        table.register_new_game(game)

        self.touch({})

        defer.returnValue(True)

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
    def on_tab_closed(self, player_id, game_id):
        """Called every time a player closes a tab."""
        table = self.game2table[game_id]
        yield table.on_tab_closed(player_id)

        defer.returnValue(True)

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

    def __init__(self, table_plugin):
        self.table_plugin = table_plugin
        self.activity_plugin = self.table_plugin.activity_plugin
        self.service = self.table_plugin.service
        self.games_ids = []
        self.last_owners_ids = []
        self.next_owner_id = None

        Pollable.__init__(self, self.service.settings.get('poll - timeout', 30))

    def register_new_game(self, game):
        """
        Registers the latest game for the table when it is created
        """

        self.games_ids.append(game.id)

        # Don't add a owner_id twice
        self.last_owners_ids = filter(lambda x: x != game.owner_id, self.last_owners_ids)
        self.last_owners_ids.insert(0, game.owner_id)

        # Defer decision on next owner to the end of the game
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

        player_game_id = self.get_game_id_from_args(args)
        table_game_id = self.get_current_game_id()
        table_game = yield self.get_current_game()

        # Player is asking from another game
        if player_game_id != table_game_id:
            next_game_id = table_game_id
            next_owner_id = table_game['owner_id']

        # Player is asking from the current table game
        else:
            if self.next_owner_id is None:
                # Only decide the next owner when a new game is needed,
                # to reduce the chances of picking a player who disconnects
                if table_game['state'] in ['complete', 'canceled']:
                    yield self.update_next_owner_id()

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
        online_players_ids = [ x for x in players_ids if self.activity_plugin.is_player_online(x) ]
        offline_players_ids = [ x for x in players_ids if not self.activity_plugin.is_player_online(x) ]

        active_players_ids = []
        inactive_players_ids = offline_players_ids
        for player_id in online_players_ids:
            tab_game_ids = yield self.service.get_tab_game_ids({'player_id': [player_id]})
            if current_game_id in tab_game_ids:
                active_players_ids.append(player_id)
            else:
                inactive_players_ids.append(player_id)

        defer.returnValue([active_players_ids, inactive_players_ids])

    @defer.inlineCallbacks
    def update_next_owner_id(self):
        """
        Chose the next player who will create a game on this table, if necessary.
        
        Returns the name of the player, and sets the self.owner_id attribute.
        """

        if self.next_owner_id is None:
            active_players_ids, inactive_players_ids = yield self.get_active_players()
            if len(active_players_ids) >= 1:
                # Take the player who was owner the longest ago (or never)
                for owner_id in self.last_owners_ids:
                    if len(active_players_ids) == 1:
                        break
                    elif owner_id in active_players_ids:
                        active_players_ids.remove(owner_id)

                self.next_owner_id = active_players_ids[0]

                # Let clients know that the next owner has been chosen
                self.touch({})

        defer.returnValue(self.next_owner_id)

    @defer.inlineCallbacks
    def on_player_disconnecting(self, player_id):
        """
        Called every time a player disconnects
        (not necessarily an active player from the current table game)
        
        Change the next owner when he disconnects
        """

        if self.next_owner_id and self.next_owner_id == player_id:
            self.next_owner_id = None
            yield self.update_next_owner_id()

    @defer.inlineCallbacks
    def on_tab_closed(self, player_id):
        """
        Called every time a player closes the tab holding
        the game corresponding to this table.
        Change the next owner if it was this player's turn.
        """

        # The action taken should be the same as when a player
        # disconnects, so just delegate to the on_player_disconnecting method.
        yield self.on_player_disconnecting(player_id)
