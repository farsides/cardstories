#
# Copyright (C) 2011 Chris McCormick <chris@mccormickit.com>
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
from twisted.python import runtime, log
from twisted.internet import defer, reactor

from cardstories.poll import pollable

# How long we retain old messages for in milliseconds
MESSAGE_EXPIRE_TIME = 3600000

class Plugin(pollable):
    """ The chat plugin implements the backend for the in-game chat system. """
    def __init__(self, service, plugins):
        # Register a function to listen to the game events. 
        self.service = service

        # Storage for our messages
        self.messages = []

        # Implement the path conventions
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], self.name())
        self.libdir = os.path.join(self.service.settings['plugins-libdir'], self.name())

        # Initialize the pollable using the recommended timeout.
        pollable.__init__(self, self.service.settings.get('poll-timeout', 300))

    def name(self):
        """ Method required by all plugins to inspect the plugin's name. """
        return 'chat'

    def preprocess(self, result, request):
        """ 
            Here we are looking for the 'message' action and we will make a new entry in the database when we receive it.
            The chat plugin is expecting a message of this format:
            request.args == { 'player_id': xxxx, 'action': "message", 'sentence': xxxxxxx }
        """
        if request.args['action'][0] == 'message':
            # remove the message action so it does not flow through
            del request.args['action'] 

            # Build the message.
            timestamp = int(runtime.seconds() * 1000)
            player_id = request.args['player_id'][0]
            sentence = request.args['sentence'][0]
            message = {"timestamp": timestamp, "player_id": player_id, "sentence": sentence}

            # Save it in our "database".
            self.messages.append(message)

            # Cull out old messages so we don't leak.
            delmessages = [m for m in self.messages if m["timestamp"] < timestamp - MESSAGE_EXPIRE_TIME]
            for m in delmessages:
                self.messages.remove(m)

            # Tell everybody connected that there's a new message.
            self.touch(request.args)

            return defer.succeed(request.args)
        else:
            # Just pass the result forward.
            return defer.succeed(result)

    def state(self, args):
        """ Tells the client about the current state - all messages since the last update. This will automatically get called by the server when the state changes. """
        return defer.succeed({"messages": [m for m in self.messages if m["timestamp"] > int(args['modified'][0])]})
