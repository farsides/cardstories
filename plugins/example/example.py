# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Loic Dachary <loic@dachary.org>
#
# Authors:
#          Loic Dachary <loic@dachary.org>
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

from cardstories.poll import Pollable

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
class Plugin(Pollable):
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
    # When the plugin is derived from pollable, the cardstories client can 
    # poll it and be notified when the plugin state changes. The plugin
    # notifies the client that its state changed by calling the touch()
    # method. The client will then ask for the current state of the plugin
    # using the state() method.
    #
    # The pollable derivation is optional. If Plugin is not derived from
    # pollable, the state method bellow will never be called and the code
    # associated with the comments where the "pollable" keyword show can
    # be commented out.
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
        # initialize the pollable using the service parameters. There is
        # no reason to improve or change these parameters.
        #
        Pollable.__init__(self, self.service.settings.get('poll-timeout', 30))

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
            # the game master chose the card or wrote the sentence.
            #
            if details['type'] == 'create':
                pass
            #
            # Received once, when the game master sets the card.
            #
            if details['type'] == 'set_card':
                pass
            #
            # Received once, when the game master writes the sentence,
            # moving the game into 'invitation' state.
            #
            if details['type'] == 'set_sentence':
                pass
            #
            # Received once, when the game is loaded during server
            # startup
            #
            if details['type'] == 'load':
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
    # All the values are strings. For instance, even the numerical
    # identifier for a card is a string and is not converted into an integer.
    #
    # The type of the parameters are documented assuming the plugin is the only
    # loaded plugin. For instance, if an authentication plugin processes
    # the request afterwards, the type of the player_id may be a string instead
    # of a numerical id.
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
            args = request.args
            self.preprocessed = args
            #
            # create a new game.
            #
            if args['action'][0] == 'create':
                args['owner_id'][0] # the player who creates the game
            #
            # set the card (game master only)
            #
            elif args['action'][0] == 'set_card':
                args['card'][0] # the numerical identifier of the chosen card
                args['game_id'][0] # the identifier of the game
                args['player_id'][0] # the game master
            #
            # set the sentence (game master only)
            # The sentence is an utf-8 encode string
            # that needs to be decoded as follows:
            #
            # sentence = args['sentence'][0].decode('utf-8')
            #
            elif args['action'][0] == 'set_card':
                args['sentence'][0] # the sentence describing the chosen card
                args['game_id'][0] # the identifier of the game
                args['player_id'][0] # the game master
            #
            # invite players to participate in the game
            #
            elif args['action'][0] == 'invite':
                args['game_id'][0] # the identifier of the game
                args['owner_id'][0] # the player who owns the game
                args['player_id'][0] # the list of invited players
            #
            # participate in the game
            #
            elif args['action'][0] == 'participate':
                args['game_id'][0] # the identifier of the game
                args['player_id'][0] # the player who wants to enter the game
            #
            # pick a card among the cards distributed to the player
            #
            elif args['action'][0] == 'pick':
                args['game_id'][0] # the identifier of the game
                args['player_id'][0] # the player who is picking  card
                args['card'][0] # the numerical identifier of the chosen card
            # 
            # the author of the game goes to the vote
            #
            elif args['action'][0] == 'voting':
                args['game_id'][0] # the identifier of the game
                args['owner_id'][0] # the player who owns the game
            #
            # vote for a card
            #
            elif args['action'][0] == 'vote':
                args['game_id'][0] # the identifier of the game
                args['player_id'][0] # the player who is voting for a card
                args['card'][0] # the numerical identifier of the chosen card
            # 
            # the author of the game publishes the game results
            #
            elif args['action'][0] == 'complete':
                args['game_id'][0] # the identifier of the game
                args['owner_id'][0] # the player who owns the game
            # 
            # request the state of the game
            #
            elif args['action'][0] == 'game':
                args['game_id'][0] # the identifier of the game
                args['player_id'][0] # the player requesting the game

            return defer.succeed(result)

    #
    # The postprocess method is registered as a deferred callback which
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
            if result.has_key('type'):
                #
                # In the following, each result['type'] matches
                # the answer to the incoming action as described
                # in the preprocess function. 
                #

                #
                # The list of invited players is the subset of the
                # list provided by the caller where the duplicates
                # have been removed.
                #
                if result['type'] == 'invite':
                    result['game_id'][0] # the identifier of the game
                    result['invited'][0] # the list of invited players
                #
                # participate in the game
                #
                elif result['type'] == 'participate':
                    result['game_id'][0] # the identifier of the game
                    result['player_id'] # the player who wants to enter the game
                #
                # pick a card among the cards distributed to the player
                #
                elif result['type'] == 'pick':
                    result['game_id'][0] # the identifier of the game
                    result['player_id'] # the player who is picking  card
                    result['card'] # the numerical identifier of the chosen card
                # 
                # the game goes to vote
                #
                elif result['type'] == 'voting':
                    result['game_id'][0] # the identifier of the game
                #
                # vote for a card
                #
                elif result['type'] == 'vote':
                    result['game_id'][0] # the identifier of the game
                    result['player_id'] # the player who is voting for a card
                    result['vote'] # the numerical identifier of the chosen card
                # 
                # the author of the game publishes the game results
                #
                elif result['type'] == 'complete':
                    result['game_id'][0] # the identifier of the game
            else:
                #
                # A game was created, the new identifier is returned
                #
                result['game_id'] # the id of the game
            return defer.succeed(result)

    #
    # pollable:
    #
    # Demonstrate how the plugin can notify the clients when 
    # its state changes.
    #
    def count(self):
        self.counter = 0
        def incr():
            self.counter += 1
            #
            # The argument of the touch method must be a map.
            # It is implemented by the pollable class and
            # the 'modified' key will be set to the unix timestamp
            # of the current time. Each client will receive a
            # copy of the map, in a JSON object.
            #
            self.touch({'info': True}) # notify the clients
        reactor.callLater(0.01, incr)

    #
    # pollable:
    #
    # The state method is called when a client requires the action=state
    # of the server and adds type=<plugin name> (type=example in this
    # example) to the query string. The args argument is a map with 
    # the following keys:
    #
    # args['modified'] = unix timestamp 
    #  return only the data that has changed after timestamp
    #  argument. It is not required to return only
    #  the delta and the method can return the full state of the plugin.
    #
    # In the context of a chat plug, the state method would be expected to
    # return the lines written since the last call to the state method.
    #
    # The return value should also contain a list of all the player_ids
    # being referenced by the state, so that the service can keep track
    # of them.
    #
    def state(self, args):
        args['modified'][0] # unix timestamp 
        players_id_list = list('1')
        state = {}
        state['counter'] = self.counter
        return defer.succeed([state, players_id_list])

