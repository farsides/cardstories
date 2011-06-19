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
# The API of the CardstoriesGame and CardstoriesServices are not documented.
# The code from other plugins should be used for inspiration.
#
class Plugin:
    #
    # Instantiated when the plugin is loaded.
    # service is an instance of CardstoriesService as found
    # in service.py. The service is not started when the plugin
    # is instantiated. 
    #
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
    # This function is registered by __init__ to listen on every
    # CardstoriesService events, as described in the body of the
    # function. The function registered to listen to
    # CardstoriesService must register itself again to catch the next
    # event.
    #
    # If accept raises an exception, it will show in the cardstories
    # log with a backtrace. Such an exception is otherwise ignored
    # and has no side effect on the other listeners.
    #
    # The event argument is an object which can be interpreted as
    # documented in the code below. All cases and data members
    # are demonstrated and the code should be used as a reference.
    #
    # The return value must be a Deferred
    #
    # It is forbidden to trigger an action on a game in the listener.
    # If a side effect is desired, it must be done using a timed function
    # instead. This limitation is imposed to prevent recursive notification
    # which would be both complex and confusing. The solo mode plugin
    # has examples of timed events that modify the course of the game.
    #
    # In the function below, the data member self.event is set according
    # to the event. This is used in the test_example.py file to ensure
    # that the sequence of events happens as documented.
    #
    # In each documented case in the function below, the data
    # that have a meaning are displayed and documented. For instance,
    # when a game is deleted:
    #
    #    elif event['type'] == 'delete':
    #        self.event = 'DELETE'
    #        event['game'] # CardstoriesGame instance
    # 
    # this means that only the event['game'] data is set and it holds
    # a CardstoriesGame instance. If a data is not documented, it must
    # be assumed to be undefined. The presence of the documented data
    # will be kept consistent for backward compatibility.
    #
    def accept(self, event):
        if event == None:
            self.event = 'NONE'
        # 
        # Received when startService() is called on CardstoriesService.
        # The ongoing games are loaded from the database (after a daemon
        # restart) before this event. The service is fully operational
        # and the event occurs before any connection is accepted from
        # clients.
        #
        elif event['type'] == 'start':
            self.event = 'START'
        #
        # Received when stopService() is about to be called on
        # CardstoriesService. Nothing has been terminated yet and all
        # client connections are active. The service will stop only
        # when the returned deferred is complete.
        #
        elif event['type'] == 'stop':
            self.event = 'STOP'
        #
        # Received when a game is about to be deleted from
        # memory. This happens shortly after a game is completed. A
        # completed game is loaded from the database only when
        # required and will be deleted after a while, if unused. As a
        # consequence, multiple delete events can be received for the
        # same game.
        #
        elif event['type'] == 'delete':
            self.event = 'DELETE'
            event['game'] # CardstoriesGame instance
        # 
        # Received when an event related to a given game occurs.
        #
        elif event['type'] == 'change':
            #
            # The event is further described in the event['details']
            # data. The event is received after the game was modified.
            # For instance, if the event received says the game
            # when to the voting state, checking the game state would
            # confirm that it is in voting state. 
            #
            # Because the listeners are forbident to have any side 
            # effect on the games, the action undertaken cannot rely
            # and does not have to worry about the order in which the
            # listeners are called. If a timed action is run to alter
            # the game state, it must take into account that other
            # plugins can do the same. A lack of coordination between
            # plugins that plan to alter the game in this way will lead
            # to an undefined results.
            #
            self.event = 'CHANGE ' + event['details']['type']
            event['game'] # CardstoriesGame instance
            details = event['details'] # description of the event
            # 
            # Received once, when the game is created and before
            # any player is connected to it.
            #
            if details['type'] == 'init':
                pass
            #
            # Received each time the author invites players.
            # It can happen multiple times for a given game. The
            # list of invited players is guaranteed to not 
            # contain duplicates. The aggregated invitations for
            # a given game does not contain duplicates.
            #
            elif details['type'] == 'invite':
                details['invited'] # list of numerical player ids
            #
            # Received each time a player is distributed cards 
            # to pick and is therefore registered as a participant
            # to the game. 
            #
            elif details['type'] == 'participate':
                details['player_id'] # numerical player id
            #
            # Received each time a player picks a card. A player
            # may pick a card multiple times and only the latest
            # is taken into account.
            #
            elif details['type'] == 'pick':
                details['player_id'] # numerical player id
                details['card'] # numerical card id
            #
            # Received once, when the author goes to voting state.
            #
            elif details['type'] == 'voting':
                pass
            #
            # Received each time a player votes for a card. A player
            # may vote for a card multiple times and only the latest
            # is taken into account.
            #
            elif details['type'] == 'vote':
                details['player_id'] # numerical player id
                details['vote'] # numerical card id
            #
            # Received once, when the author goes to complete state.
            #
            elif details['type'] == 'complete':
                pass
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
