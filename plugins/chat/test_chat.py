# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Chris McCormick <chris@mccormick.cx>
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
import sys, os, shutil
sys.path.insert(0, os.path.abspath("../..")) # so that for M-x pdb works
import sqlite3
from time import sleep, strftime

from twisted.python import runtime
from twisted.trial import unittest, runner, reporter
from twisted.internet import reactor, defer

from cardstories.service import CardstoriesService
from plugins.chat.chat import Plugin

# fake a request object holding the arguments we specify
class Request:
    
    def __init__(self, **kwargs):
        self.args = kwargs

class ChatTest(unittest.TestCase):

    # initialise our test with a service that we can use during testing and a testing database
    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)

        # Make sure the log dir has an empty 'chat/' subdir
        self.test_logdir = 'test_logdir.tmp'
        if os.path.exists(self.test_logdir):
            shutil.rmtree(self.test_logdir)
        os.mkdir(self.test_logdir)
        os.mkdir(os.path.join(self.test_logdir, 'chat'))

        self.service = CardstoriesService({'db': self.database,
                                           'plugins-confdir': 'CONFDIR',
                                           'plugins-libdir': 'LIBDIR',
                                           'plugins-logdir': self.test_logdir,
                                           'static': 'STATIC'
                                           })
        self.service.startService()

    def tearDown(self):
        # kill the service we started before the test
        return self.service.stopService()
    
    @defer.inlineCallbacks
    def complete_game(self):
        self.winner_card = winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        self.player1 = 16
        for player_id in ( self.player1, 17 ):
            yield self.service.participate({ 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.service.player2game({ 'action': ['player2game'],
                                                      'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            card = player['cards'][0]
            yield self.service.pick({ 'action': ['pick'],
                                      'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [card] })
        
        yield self.service.voting({ 'action': ['voting'],
                                    'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })
        winner_id = self.player1
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [game['game_id']],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = 17
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [game['game_id']],
                                  'player_id': [loser_id],
                                  'card': [120] })
        self.assertTrue(self.service.games.has_key(game['game_id']))
        yield self.service.complete({ 'action': ['complete'],
                                      'game_id': [game['game_id']],
                                      'owner_id': [owner_id] })
        self.assertFalse(self.service.games.has_key(game['game_id']))
        defer.returnValue(True)
    
    @defer.inlineCallbacks
    def test00_preprocess_noop(self):
        # create a new instance of the plugin and make sure it's the right type
        chat_instance = Plugin(self.service, [])
        self.assertEquals(chat_instance.name(), 'chat')
        # run a game to get into a realistic situation
        yield self.complete_game()
        # run the preprocess method and make sure it does not affect anything during a normal 'game' event
        result_in = 'RESULT'
        result_out = yield chat_instance.preprocess(result_in, Request(action = ['game']))
        self.assertEquals(result_in, result_out)

    @defer.inlineCallbacks
    def test01_add_message(self):
        # new instance of the chat plugin to test
        chat_instance = Plugin(self.service, [])
        # create a message event request
        player_id = 200
        sentence = "This is my sentence!"
        now = int(runtime.seconds() * 1000)
        request = Request(action = ['message'], player_id = [player_id], sentence=[sentence])
        # verify we have no messages yet
        self.assertEquals(len(chat_instance.messages), 0)
        # run the request
        result = yield chat_instance.preprocess(True, request)
        # verify we now have one message
        self.assertEquals(len(chat_instance.messages), 1)
        # verify the event has been removed from the pipeline
        self.assertFalse(request.args.has_key('action'))
        # verify the message we added is in the list
        self.assertEquals(chat_instance.messages[0]["player_id"], player_id)
        self.assertEquals(chat_instance.messages[0]["sentence"], sentence)
        # check that the message has been recorded in log file
        with open(os.path.join(self.test_logdir, 'chat', '%s.log' % strftime('%Y-%m-%d'))) as f:
            lines = f.readlines()
            self.assertEquals(len(lines), 1)
            self.assertIn(sentence, lines[0])
            self.assertIn('player_%d' % player_id, lines[0])
    
    
    @defer.inlineCallbacks
    def test02_check_added_message_after_now(self):
        # new instance of the chat plugin to test
        chat_instance = Plugin(self.service, [])
        # create a message event request
        player_id = 200
        sentence = "This is my sentence!"
        now = int(runtime.seconds() * 1000)
        request = Request(action = ['message'], player_id = [player_id], sentence=[sentence])
        # run the request
        result = yield chat_instance.preprocess(True, request)
        # check to make sure no message is returned if we ask for now or later
        state = yield chat_instance.state({"modified": [now]})
        self.assertTrue(state.has_key('messages'))
        self.assertEquals(len(state['messages']), 0)
    
    @defer.inlineCallbacks
    def test03_check_added_message_before_now(self):
        # new instance of the chat plugin to test
        chat_instance = Plugin(self.service, [])
        # create a message event request
        player_id = 200
        sentence = "This is my sentence!"
        now = int(runtime.seconds() * 1000)
        request = Request(action = ['message'], player_id = [player_id], sentence=[sentence])
        # run the request
        result = yield chat_instance.preprocess(True, request)
        # check to make sure no message is returned if we ask for now or later
        state = yield chat_instance.state({"modified": [now - 1]})
        self.assertEquals(len(state['messages']), 1)
        self.assertEquals(state['messages'][0]['player_id'], player_id)
        self.assertEquals(state['messages'][0]['sentence'], sentence)

    @defer.inlineCallbacks
    def test04_check_multiple_messages(self):
        # new instance of the chat plugin to test
        chat_instance = Plugin(self.service, [])
        # create a message event request
        player_ids = [200, 220, 999]
        sentences = ["This is my sentence!", "Yeah another test hello.", "Ping ping poing pong."]
        when = []
        for i in range(3):
            when.append(int(runtime.seconds() * 1000))
            request = Request(action = ['message'], player_id = [player_ids[i]], sentence=[sentences[i]])
            # run the request
            result = yield chat_instance.preprocess(True, request)
        # check to make sure no message is returned if we ask for now or later
        # we check right back to one second ago to make sure all recently added messages are caught
        state = yield chat_instance.state({"modified": [when[-1] - 1000]})
        self.assertEquals(len(state['messages']), 3)
        for i in range(3):
            self.assertEquals(state['messages'][i]['player_id'], player_ids[i])
            self.assertEquals(state['messages'][i]['sentence'], sentences[i])

    @defer.inlineCallbacks
    def test05_check_half_of_multiple_messages(self):
        # new instance of the chat plugin to test
        chat_instance = Plugin(self.service, [])
        # create a message event request
        player_ids = [200, 220, 999]
        sentences = ["This is my sentence!", "Yeah another test hello.", "Ping ping poing pong."]
        when = []
        for i in range(3):
            sleep(0.1)
            when.append(int(runtime.seconds() * 1000))
            request = Request(action = ['message'], player_id = [player_ids[i]], sentence=[sentences[i]])
            # run the request
            result = yield chat_instance.preprocess(True, request)
        # check to make sure no message is returned if we ask for now or later
        # we check right back to one second ago to make sure all recently added messages are caught
        state = yield chat_instance.state({"modified": [when[-1] - 150]})
        # this time because of the 100ms delay between messages, and only checking to 150ms ago
        # we should only get the last two messages
        self.assertEquals(len(state['messages']), 2)
        for i in range(2):
            self.assertEquals(state['messages'][i]['player_id'], player_ids[i + 1])
            self.assertEquals(state['messages'][i]['sentence'], sentences[i + 1])
    
    @defer.inlineCallbacks
    def test06_touch_state(self):
        player_id = 200
        sentence = "This is my sentence!"
        # new instance of chat plugin to run the test against
        chat_instance = Plugin(self.service, [])
        # put the chat instance into the service's pollable_plugins
        self.service.pollable_plugins.append(chat_instance)
        # flag to signify whether the callback has run
        self.called = False
        # service to poll instance waiting for chat
        d = self.service.poll({'action': ['poll'], 'type': ['chat'], 'modified': [chat_instance.get_modified()]})
        # callback which runs once the chat plugin calls touch()
        def check(event):
            self.called = True
        d.addCallback(check)
        # make sure our flag is false before we run
        self.assertFalse(self.called)
        # run the test request
        request = Request(action = ['message'], player_id = [player_id], sentence=[sentence])
        result = yield chat_instance.preprocess(True, request)
        yield d
        # make sure the flag is now set after we've run the test
        self.assertTrue(self.called)

    @defer.inlineCallbacks
    def test07_notification_messages(self):
        # new instance of chat plugin to run the test against
        chat_instance = Plugin(self.service, [])

        self.count = 0
        def build_message(self, message): 
            """
            message == {'type': 'notification',
                        'game_id': GAME_ID,
                        'player_id': 'OWNER_ID',
                        'sentence': 'SENTENCE'}

            """
            self.count += 1
            self.assertEquals(self.count, 1)
            self.assertEquals(message['type'], 'notification')
            self.assertEquals(message['player_id'], '15')
            self.assertEquals(message['sentence'], 'SENTENCE')

        # build_message should only be called once, upon game creation.
        chat_instance.build_message = build_message
        # run a game to get into a realistic situation
        yield self.complete_game()

    @defer.inlineCallbacks
    def test08_nonascii_characters(self):
        # new instance of the chat plugin to test
        chat_instance = Plugin(self.service, [])
        # create a message event request
        player_id = 200
        # The sentence is a 'str' object. Create it by encoding a unicode string.
        unicode_sentence = u"你好 Matjaž Gregorič"
        sentence_bytes = unicode_sentence.encode('utf-8')
        request = Request(action = ['message'], player_id = [player_id], sentence=[sentence_bytes])
        # run the request
        result = yield chat_instance.preprocess(True, request)
        # check that the message has been recorded in log file
        with open(os.path.join(self.test_logdir, 'chat', '%s.log' % strftime('%Y-%m-%d'))) as f:
            lines = f.readlines()
            self.assertIn(unicode_sentence, lines[0].decode('utf-8'))

    @defer.inlineCallbacks
    def test09_escape_html(self):
        # new instance of the chat plugin to test
        chat_instance = Plugin(self.service, [])
        # create a message event request
        player_id = 201
        naughty_sentence = '<script>alert("haha!")</script>'
        now = int(runtime.seconds() * 1000)
        request = Request(action = ['message'], player_id = [player_id], sentence=[naughty_sentence])
        # run the request
        result = yield chat_instance.preprocess(True, request)
        # check to make sure our naughty message is returned properly escaped
        state = yield chat_instance.state({"modified": [now - 1]})
        self.assertEquals(state['messages'][0]['player_id'], player_id)
        self.assertEquals(state['messages'][0]['sentence'], '&lt;script&gt;alert("haha!")&lt;/script&gt;')


def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(ChatTest))

    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

# Interpreted by emacs
# Local Variables:
# compile-command: "python-coverage -e ; PYTHONPATH=../.. python-coverage -x test_chat.py ; python-coverage -m -a -r chat.py"
# End:

