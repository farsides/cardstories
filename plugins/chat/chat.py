# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Farsides <contact@farsides.com>
#
# Authors:
#          Chris McCormick <chris@mccormick.cx>
#          Matjaz Gregoric <mtyaka@gmail.com>
#          Xavier Antoviaque <xavier@antoviaque.org>
#          Adolfo R. Brandes <arbrandes@gmail.com>
#          Côme Bernigaud <come.bernigaud@laposte.net>
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
import os, time, codecs, cgi
from lxml import objectify
from twisted.python import runtime, log
from twisted.internet import defer, reactor

from django.utils.html import urlize

from cardstories.poll import Pollable
from cardstories.helpers import Observable

# How long we retain old messages for in milliseconds
MESSAGE_EXPIRE_TIME = 3600000

class Plugin(Pollable):
    """
    The chat plugin implements the backend for the in-game chat system.
    
    """
    def __init__(self, service, plugins):
        # Register a function to listen to the game events. 
        self.service = service
        self.service.listen().addCallback(self.self_notify)

        # Storage for our messages
        self.messages = []

        # Implement the path conventions
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], self.name())
        self.libdir = os.path.join(self.service.settings['plugins-libdir'], self.name())
        self.logdir = os.path.join(self.service.settings['plugins-logdir'], self.name())

        # Initialize logdir, and make sure we have write permissions.
        # If not, turn off logging.
        self.logging = True
        if not os.path.exists(self.logdir):
            try:
                os.makedirs(self.logdir)
            except OSError:
                self.logging = False
        elif not os.access(self.logdir, os.W_OK):
            self.logging = False

        # Initialize the pollable using the recommended timeout.
        Pollable.__init__(self, self.service.settings.get('poll-timeout', 30))

    def name(self):
        """
        Method required by all plugins to inspect the plugin's name.
        
        """
        return 'chat'

    def self_notify(self, changes):
        """
        If a 'change' notification is receive of the 'init' type, call the
        appropriate method and reinsert our listen() callback so we get called
        again later, when there's a new event.

        """
        d = defer.succeed(True)
        if changes != None and changes['type'] == 'change':
            details = changes['details']
            if details['type'] == 'set_sentence' or (details['type'] == 'load' and details['sentence']):
                d = self.init(changes['game'], details)
        self.service.listen().addCallback(self.self_notify)
        return d

    def build_message(self, message):
        timestamp = int(runtime.seconds() * 1000)
        message.update({'timestamp': timestamp})

        # Save it in our "database".
        self.messages.append(message)

        # Log the message
        if self.logging:
            self.log_message(message)

        # Cull out old messages so we don't leak.
        delmessages = [m for m in self.messages
                       if m['timestamp'] < timestamp - MESSAGE_EXPIRE_TIME]
        for m in delmessages:
            self.messages.remove(m)

    def log_message(self, message):
        """
        Write down the message to a text file on the filesystem.
        The `message` is expected to be a unicode object.
        """

        log_time = time.strftime('%d-%m-%Y %H:%M:%S')
        if message['type'] == 'chat':
            log_text = '%s <player_%s> %s\n' % (log_time, message['player_id'], message['sentence'])
        elif message['type'] == 'notification':
            log_text = '%s ** player_%s created the game "%s" (id=%d)\n' % (log_time, message['player_id'], message['sentence'], message['game_id'])

        log_filename = '%s.log' % time.strftime('%Y-%m-%d')
        log_filepath = os.path.join(self.logdir, log_filename)

        with codecs.open(log_filepath, mode='ab', encoding='utf-8', errors='replace', buffering=1) as f:
            f.write(log_text)

    def init(self, game, details):
        """
        Build a 'notification' type message and notify everybody to pick it up.
        The message format should be:

        message == {'type': 'notification',
                    'game_id': 10,
                    'player_id': 'Neo',
                    'sentence': 'What is the Matrix?'}

        """
        message = {'type': 'notification',
                   'game_id': game.id,
                   'player_id': game.owner_id,
                   'sentence': details['sentence']}
        self.build_message(message);

        # Notify pollers.
        self.touch({})

        return defer.succeed(True)

    def preprocess(self, result, request):
        """ 
        Here we are looking for the 'message' action and we will make a new
        entry in the database when we receive it.  The chat plugin is expecting
        a message of this format:

        message == {'type': 'chat',
                    'player_id': 'Scotty',
                    'sentence': 'Hello, computer?'}

        """
        if 'action' in request.args and request.args['action'][0] == 'message':
            # Remove the message action so it does not flow through.
            del request.args['action']

            # Sentence arg in the request is a utf-8 encoded string of bytes.
            # Decode it into an unicode object.
            sentence = request.args['sentence'][0].decode('utf8')
            # Escape HTML characters.
            sentence = cgi.escape(sentence)

            # Make links from urls
            sentence = urlize(sentence, None)
            # Add target=_blank to links, so that they does not open in the same window/tab
            sentence = sentence.replace('<a ', '<a target="_blank" ')

            # Build the message.
            message = {'type': 'chat',
                       'player_id': request.args['player_id'][0],
                       'sentence': sentence}
            self.build_message(message)

            # Tell everybody connected that there's a new message.
            self.touch(request.args)

            return defer.succeed(request.args)
        else:
            # Just pass the result forward.
            return defer.succeed(result)

    def state(self, args):
        """
        Tells the client about the current state - all messages since the
        last update. This will automatically get called by the server when the
        state changes.
        """

        messages = []
        players_id_list = []

        for m in self.messages:
            if m["timestamp"] > int(args['modified'][0]):
                messages.append(m.copy())
                players_id_list.append(m['player_id'])

        return defer.succeed([{"messages": messages},
                              players_id_list])


