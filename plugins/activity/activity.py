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

# Imports ########################################################################

import os
from twisted.internet import defer, reactor

from cardstories.poll import Pollable
from cardstories.helpers import Observable


# Classes ########################################################################

class Plugin(Pollable, Observable):
    """
    Monitors the activity of players (online/offline)
    
    """
    def __init__(self, service, plugins):
        self.service = service
        self.observers = []
        self.online_players = {}

        # Depends on the chat plugin (monitors active polls on the chat)
        for plugin in plugins:
            if plugin.name() == 'chat':
                self.chat_plugin = plugin
        assert self.chat_plugin

        self.chat_plugin.listen().addCallback(self.on_chat_notification)

        # Implement the path conventions
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], self.name())
        self.libdir = os.path.join(self.service.settings['plugins-libdir'], self.name())

        # Initialize the pollable using the recommended timeout.
        Pollable.__init__(self, self.service.settings.get('poll-timeout', 30))

    def name(self):
        """
        Method required by all plugins to inspect the plugin's name.
        
        """
        return 'activity'

    def on_chat_notification(self, changes):
        """
        Listen to chat notifications to know when polls are started/ended
        """

        d = defer.succeed(True)

        if changes != None and changes['type'] == 'poll_start':
            self.on_chat_poll_start(int(changes['player_id']))

        if changes != None and changes['type'] == 'poll_end':
            self.on_chat_poll_end(int(changes['player_id']))

        self.chat_plugin.listen().addCallback(self.on_chat_notification)
        return d

    def on_chat_poll_start(self, player_id):
        """
        Called when a new chat poll is initiated by a player.
        Mark the player as being online.
        """

        if player_id not in self.online_players:
            self.online_players[player_id] = { 'active_polls': 1 }
            self.notify({'type': 'player_connecting',
                         'player_id': player_id})
        else:
            self.online_players[player_id]['active_polls'] += 1


    def on_chat_poll_end(self, player_id):
        """
        Called when a chat poll is dropped. 
        Mark the player as being offline if he doesn't have another active poll 
        and doesn't start a new one quickly after (need to give time to reconnect)
        """

        self.online_players[player_id]['active_polls'] -= 1

        def on_poll_resume_timeout():
            if player_id in self.online_players and self.online_players[player_id]['active_polls'] <= 0:
                del self.online_players[player_id]

            if player_id not in self.online_players:
                self.notify({'type': 'player_disconnecting',
                             'player_id': player_id})

        if self.online_players[player_id]['active_polls'] <= 0:
            # give X seconds to start another poll
            reactor.callLater(15, on_poll_resume_timeout)

    def state(self, args):
        """
        Shows the players currently online, along with the number of active chat polls
        """

        return defer.succeed([{"online_players": self.online_players}, []])

    def is_player_online(self, player_id):
        """
        Checks if the player is currently online
        """

        return player_id in self.online_players

