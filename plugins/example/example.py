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
from twisted.python import runtime
from twisted.internet import defer, reactor

#
# The plugin must be a single file (such as this example) that can be
# loaded in two ways:
#
# A) If --plugins-dir=/directory and --plugins=example then
#    the plugin will be loaded from /directory/example/example.py
# B) If --plugins=/somewhere/example.py 
#    the plugin will be loaded from /somewhere/example.py
#   
# cardstories will then instantiante the Plugin class as follows:
#     Plugin(service, plugins)
# 
# The plugin is reserved two directories.
# One in --plugins-confdir to store configuration files. 
# One in --plugins-libdir to store data files such as a database.
# For both of them it must use a directory name that is the same
# as the plugin name. For instance:
# If --plugins-confidir=/etc/cardstories the example plugin directory
# is /etc/cardstories/example.
# If --plugins-libdir=/var/lib/cardstories the example plugin directory
# is /var/lib/cardstories/example.
#
class Plugin:
    #
    # Instantiated when the plugin is loaded.
    # service is an instance of CardstoriesService as found
    # in service.py.
    # plugins is a list of plugin instances, in the order in
    # which they are mentionned in the --plugins option. 
    # If --plugins="a b" then it will be called:
    #
    # plugins = []
    # a.Plugin(service, plugins)
    # plugins.append(a)
    # b.Plugin(service, plugins)
    # plugins.append(a)
    #
    # and so on
    #
    def __init__(self, service, plugins):
        # 
        # The example depends on another plugin and checks
        # that it has been loaded before it. It relies on the
        # name() method to identify the plugin.
        #
        for plugin in plugins:
            if plugin.name() == 'another':
                self.another = plugin
        assert self.another
        #
        # Register a function to listen to the game events. 
        # check the documentation of the self_notify method.
        #
        self.service = service
        self.service.listen().addCallback(self.accept)
        #
        # Implement the path conventions as described above ( look for plugins-confdir )
        #
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], self.name())
        self.libdir = os.path.join(self.service.settings['plugins-libdir'], self.name())

    #
    # Must return a string that is the name of the plugin. It 
    # will be used to match the strings found in the
    # --plugins-pre-process and --plugins-post-process 
    # options.
    #
    def name(self):
        return 'example'

    #
    # 
    #
    def accept(self, event):
        if event == None:
            self.event = 'NONE'
        # startService() was called on CardstoriesService
        elif event['type'] == 'start':
            self.event = 'START'
        # stopService() is about to be called on CardstoriesService
        elif event['type'] == 'stop':
            self.event = 'STOP'
        # a game is about to be deleted from memory
        elif event['type'] == 'delete':
            self.event = 'DELETE'
            event['game'] # CardstoriesGame instance
        # a game was modified
        elif event['type'] == 'change':
            self.event = 'CHANGE ' + event['details']['type']
            event['game'] # CardstoriesGame instance
            # 
            if event['details']['type'] == 'init':
                pass
            # a player is given cards to pick
            elif event['details']['type'] == 'participate':
                event['details']['player_id'] # numerical player id
            # the author went to voting state
            elif event['details']['type'] == 'voting':
                pass
            # the player picks a card
            elif event['details']['type'] == 'pick':
                event['details']['player_id'] # numerical player id
                event['details']['card'] # numerical card id
            # the player votes for a card
            elif event['details']['type'] == 'vote':
                event['details']['player_id'] # numerical player id
                event['details']['vote'] # numerical card id
            # the author went to game complete state
            elif event['details']['type'] == 'complete':
                pass
            # the author invited players to play
            elif event['details']['type'] == 'invite':
                event['details']['invited'] # list of numerical player ids
        self.service.listen().addCallback(self.accept)
        return defer.succeed(True)

    @defer.inlineCallbacks
    def preprocess(self, result, request):
        for (key, values) in request.args.iteritems():
            if key == 'player_id' or key == 'owner_id':
                new_values = []
                for value in values:
                    value = value.decode('utf-8')
                    row = yield self.db.runQuery("SELECT id FROM players WHERE name = ?", [ value ])
                    if len(row) == 0:
                        id = yield self.db.runInteraction(self.create, value)
                    else:
                        id = row[0][0]
                    new_values.append(id)
                request.args[key] = new_values
        defer.returnValue(result)

    @defer.inlineCallbacks
    def postprocess(self, result):
        if result and result.has_key('players'):
            for player in result['players']:
                row = yield self.db.runQuery("SELECT name FROM players WHERE id = ?", [ player[0] ])
                player[0] = row[0][0]
        if result and result.has_key('invited') and result['invited']:
            invited = result['invited'];
            for index in range(len(invited)):
                row = yield self.db.runQuery("SELECT name FROM players WHERE id = ?", [ invited[index] ])
                invited[index] = row[0][0]
        defer.returnValue(result)
