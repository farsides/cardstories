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

# how long we retain old messages for in milliseconds
MESSAGE_EXPIRE_TIME = 3600000

class Plugin(pollable):
    """ The chat plugin implements the backend for the in-game chat system. """
    def __init__(self, service, plugins):
        # Register a function to listen to the game events. 
        self.service = service
        # storage for our messages
        self.messages = []
        # Implement the path conventions
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], self.name())
        self.libdir = os.path.join(self.service.settings['plugins-libdir'], self.name())
        # initialize the pollable using the service parameters. There is
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
            # convenient access to passed in data
            args = request.args
            # put this sentence into the database
            sentence = args['sentence'][0] # the sentence that was said
            player_id = args['player_id'][0] # the player who said it
            result = {"when": int(runtime.seconds() * 1000), "player_id": player_id, "sentence": sentence}
            self.messages.append(result)
            # log the chat message for later
            log.msg('chat: ' + str(player_id) + " - " + str(sentence))
            # cull out very old messages to stop memory leaks
            delmessages = [m for m in self.messages if int(runtime.seconds() * 1000) > m["when"] + MESSAGE_EXPIRE_TIME]
            for m in delmessages:
                self.messages.remove(m)
            # tell everybody connected about the new sentence
            #def sendall():
            #    self.touch(request.args)
            #reactor.callLater(0.01, sendall)
            self.touch(request.args)
            return defer.succeed(args)
        else:
            return defer.succeed(result)

    def state(self, args):
        """ Tells the client about the current state - all messages since the last update. This will automatically get called by the server when the state changes. """
        return defer.succeed({"messages": [m for m in self.messages if args['modified'][0] < m["when"]]})

