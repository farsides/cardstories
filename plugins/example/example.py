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
    # The accept function is registered by __init__ to listen on every
    # CardstoriesService events, as described in the body of the
    # function. It must register itself again to catch the next event.
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
        # 
        # Received when startService() is called on CardstoriesService.
        # The ongoing games are loaded from the database (after a daemon
        # restart) before this event. The service is fully operational
        # and the event occurs before any connection is accepted from
        # clients.
        #
        if event['type'] == 'start':
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

    #
    # The preprocess method will be called if the plugin name ( as
    # returned by the name() method) is listed in the --plugins-pre-process
    # argument. For instance if
    #
    # --plugins-pre-process="auth example"
    #
    # is given, the 
    #   auth.Plugin().preprocess
    # method will be called and immediately after the
    #   example.Plugin().preprocess
    # method will be campled. The order in which the methods are called matches
    # the order in which the plugin name show in the option. 
    # The return value of the first plugin preprocess method is given as an
    # argument to the second plugin process method, and so on. Each preprocess
    # method is expected to have side effects on the incoming structures. For
    # instance, the auth module is expected to replace the human readable 
    # strings with numerical identifiers.
    #
    # The same applies to the postprocess method (
    # --plugins-post-process ) and the differences between the two are
    # document before each function.
    #

    #
    # The preprocess method is registered as a deferred callback which
    # is triggered when a client request is received by the
    # cardstories server and before it is handled by the
    # CardstoriesService handle function.
    #
    # The result argument is the return value of the previous callback.
    # The request argument is a Request instance, as defined by twisted.web
    #
    # The request argument contains a args member that is a dictionary
    # where keys are arguments extracted from the QUERY_STRING. For instance
    #
    # QUERY_STRING=foo=1&foo=2&bar=3
    #
    # will translate into
    #
    # request.args == { 'foo': ['1', '2'], 'bar': ['3'] }
    #
    # After the last plugin preprocess method returns, the request
    # argument is given to the CardstoriesService handle method for
    # processing, together with the returned result.
    #
    # If the function throws, it will show a full traceback in the logs,
    # abort the request and a Server Error (500) will be returned, with the
    # traceback. 
    #
    def preprocess(self, result, request):
        #
        # This is an example of action that is intercepted by a plugin, 
        # is has no meaning outside this plugin.
        #
        if request.args['action'][0] == 'echo':
            # 
            # Deleting the request.args dictionary entry "action" 
            # is the recommended way to intercept a request and 
            # tell CardstoriesService to not do anything with it. 
            # When this is done, the result argument will be transparently 
            # returned to the user.
            # 
            del request.args['action'] 
            #
            # The same request object will be given to the next plugin in
            # the callback queue. It will therefore see each value with a
            # trailing X appended to it.  This is the technique used to
            # translated the human readable user name into a numerical
            # id.
            #
            for (key, values) in request.args.iteritems():
                request.args[key] = map(lambda value: value + 'X', values)
            #
            # Because the 'action' dictionary entry has been removed above,
            # the value returned by the preprocess function will be transparently
            # used as the body of the request answer. In this case the incoming
            # arguments are echoed back to the client.
            #
            return defer.succeed(request.args)
        else:
            self.preprocessed = request.args
            return defer.succeed(result)

    #
    # The preprocess method is registered as a deferred callback which
    # is triggered after a request has been processed by the
    # CardstoriesService handle function.
    #
    # If the function throws, it will show a full traceback in the logs,
    # abort the request and a Server Error (500) will be returned, with the
    # traceback. 
    #
    def postprocess(self, result):
        if result.has_key('echo') and result['echo'][0] == 'yesX':
            #
            # If the result is an intercepted echo from the preprocess
            # method that was passed to postprocess transparently, augment it.
            #
            result['MORE'] = 'YES'
            return defer.succeed(result)
        else:
            self.postprocessed = result
            return defer.succeed(result)
