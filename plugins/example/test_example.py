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
import sys
import os
sys.path.insert(0, os.path.abspath("../..")) # so that for M-x pdb works

from twisted.trial import unittest, runner, reporter
from twisted.internet import reactor, defer
from twisted.web import server

from cardstories.site import CardstoriesTree, CardstoriesSite, CardstoriesResource
from cardstories.service import CardstoriesService
from plugins.example import example

class Request:

    def __init__(self, **kwargs):
        self.args = kwargs

class AnotherPlugin:

    def name(self):
        return "another"

class ExampleTestInit(unittest.TestCase):

    def test00_init(self):
        class TestService():
            def listen(self):
                return defer.succeed(True)

class Transport:
    host = None

    def getPeer(self):
        return None
    def getHost(self):
        return self.host

class Channel:
    def __init__(self, site):
        self.transport = Transport()
        self.site = site

    def requestDone(self, request):
        pass

class ExampleTest(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)
        self.service = CardstoriesService({'db': self.database,
                                           'plugins-confdir': 'CONFDIR',
                                           'plugins-libdir': 'LIBDIR',
                                           'static': 'STATIC'
                                           })

    @defer.inlineCallbacks
    def complete_game(self, send):
        self.winner_card = winner_card = 5
        self.player1 = 1001
        self.player2 = 1002
        self.owner_id = 1003
        self.sentence = sentence = 'SENTENCE'
        game = yield send('create', { 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [self.owner_id]})
        self.game_id = game['game_id']
        yield send('invite', { 'action': ['invite'],
                                    'game_id': [self.game_id],
                                    'player_id': [self.player1],
                                    'owner_id': [self.owner_id] })
        for player_id in (self.player1, self.player2):
            yield send('participate', { 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [self.game_id] })
            player = yield self.service.player2game({ 'action': ['player2game'],
                                                      'player_id': [player_id],
                                                      'game_id': [self.game_id] })
            card = player['cards'][0]
            yield send('pick', { 'action': ['pick'],
                                      'player_id': [player_id],
                                      'game_id': [self.game_id],
                                      'card': [card] })

        yield send('voting', { 'action': ['voting'],
                                    'game_id': [self.game_id],
                                    'owner_id': [self.owner_id] })
        winner_id = self.player1
        yield send('vote', { 'action': ['vote'],
                                  'game_id': [self.game_id],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = self.player2
        yield send('vote', { 'action': ['vote'],
                                  'game_id': [self.game_id],
                                  'player_id': [loser_id],
                                  'card': [120] })
        self.assertTrue(self.service.games.has_key(self.game_id))
        yield send('complete', { 'action': ['complete'],
                                      'game_id': [self.game_id],
                                      'owner_id': [self.owner_id] })
        self.assertFalse(self.service.games.has_key(self.game_id))
        defer.returnValue(True)

    def test00_init(self):
        plugin = example.Plugin(self.service, [ AnotherPlugin() ])
        self.assertEqual(plugin.service, self.service)
        self.assertSubstring('example', plugin.confdir)
        self.assertSubstring('example', plugin.libdir)

    @defer.inlineCallbacks
    def test01_accept(self):
        plugin = example.Plugin(self.service, [ AnotherPlugin() ])
        self.events = []
        def accept(event):
            self.service.listen().addCallback(accept)
            self.events.append(plugin.event)
            return defer.succeed(True)
        self.service.listen().addCallback(accept)
        self.service.startService()
        yield self.complete_game(lambda action, args: getattr(self.service, action)(args))
        yield self.service.stopService()
        self.assertEqual(self.events, ['START',
                                       'CHANGE create',
                                       'CHANGE invite',
                                       'CHANGE participate',
                                       'CHANGE pick',
                                       'CHANGE participate',
                                       'CHANGE pick',
                                       'CHANGE voting',
                                       'CHANGE vote',
                                       'CHANGE vote',
                                       'CHANGE complete',
                                       'DELETE',
                                       'STOP'])

        # 'load' event
        self.events = []
        self.service.listen().addCallback(accept)
        self.service.startService()
        game = yield send('create', { 'card': [1],
                                   'sentence': ['SENTENCE'],
                                   'owner_id': [2]})
        yield self.service.stopService()
        self.service.startService()
        self.assertEqual(self.events, ['START',
                                       'CHANGE create',
                                       'STOP',
                                       'START',
                                       'CHANGE load',
                                       'STOP'])

    def test02_transparent_transform(self):
        self.site = CardstoriesSite(CardstoriesTree(self.service),
                                    { 'plugins-pre-process': 'example',
                                      'plugins-post-process': 'example' },
                                    [ example.Plugin(self.service, [ AnotherPlugin() ]) ])
        r = server.Request(Channel(self.site), True)
        r.site = r.channel.site
        input = ''
        r.gotLength(len(input))
        r.handleContentChunk(input)
        r.queued = 0
        d = r.notifyFinish()
        def finish(result):
            self.assertSubstring('\r\n\r\n{"arg1": ["val10X", "val11X"], "arg2": ["val20X"], "MORE": "YES", "echo": ["yesX"]}', r.transport.getvalue())
        d.addCallback(finish)
        r.requestReceived('GET', '/resource?action=echo&echo=yes&arg1=val10&arg1=val11&arg2=val20', '')
        return d

    @defer.inlineCallbacks
    def test03_pipeline(self):
        plugin = example.Plugin(self.service, [ AnotherPlugin() ])
        resource = CardstoriesResource(self.service)
        self.site = CardstoriesSite(CardstoriesTree(self.service),
                                    { 'plugins-pre-process': 'example',
                                      'plugins-post-process': 'example' },
                                    [ plugin ])
        self.collected = []
        def collect(result):
            self.collected.append([ plugin.preprocessed, plugin.postprocessed ])
            return result
        def send(action, args):
            args['action'] = [action];
            request = server.Request(Channel(self.site), True)
            request.site = self.site
            request.args = args
            request.method = 'GET'
            d = resource.wrap_http(request)
            d.addCallback(collect)
            return d
        self.service.startService()
        yield self.complete_game(send)
        yield self.service.stopService()
        count = 0
        self.assertEquals(self.collected[count],
                          [{'action': ['create'],
                            'card': [self.winner_card],
                            'owner_id': [self.owner_id],
                            'sentence': [self.sentence]},
                           {'game_id': self.game_id}]);
        count += 1
        del self.collected[count][1]['modified']
        self.assertEquals(self.collected[count],
                          [{'action': ['invite'],
                            'game_id': [self.game_id],
                            'owner_id': [self.owner_id],
                            'player_id': [self.player1]},
                           {'game_id': [self.game_id],
                            'invited': [self.player1],
                            'type': 'invite'}]);
        count += 1
        del self.collected[count][1]['modified']
        self.assertEquals(self.collected[count],
                          [{'action': ['participate'],
                            'game_id': [self.game_id],
                            'player_id': [self.player1]},
                           {'game_id': [self.game_id],
                            'player_id': self.player1,
                            'type': 'participate'}]);
        count += 1
        del self.collected[count][1]['modified']
        player1_card = self.collected[count][0]['card'][0]
        self.assertEquals(self.collected[count],
                          [{'action': ['pick'],
                            'card': [player1_card],
                            'game_id': [self.game_id],
                            'player_id': [self.player1]},
                           {'card': player1_card,
                            'game_id': [self.game_id],
                            'player_id': self.player1,
                            'type': 'pick'}]);
        count += 1
        del self.collected[count][1]['modified']
        self.assertEquals(self.collected[count],
                          [{'action': ['participate'],
                            'game_id': [self.game_id],
                            'player_id': [self.player2]},
                           {'game_id': [self.game_id],
                            'player_id': self.player2,
                            'type': 'participate'}]);
        count += 1
        del self.collected[count][1]['modified']
        player2_card = self.collected[count][0]['card'][0]
        self.assertEquals(self.collected[count],
                          [{'action': ['pick'],
                            'card': [player2_card],
                            'game_id': [self.game_id],
                            'player_id': [self.player2]},
                           {'card': player2_card,
                            'game_id': [self.game_id],
                            'player_id': self.player2,
                            'type': 'pick'}]);
        count += 1
        del self.collected[count][1]['modified']
        self.assertEquals(self.collected[count],
                          [{'action': ['voting'],
                            'game_id': [self.game_id],
                            'owner_id': [self.owner_id]},
                           {'game_id': [self.game_id], 'type': 'voting'}]);
        count += 1
        del self.collected[count][1]['modified']
        self.assertEquals(self.collected[count],
                          [{'action': ['vote'],
                            'card': [self.winner_card],
                            'game_id': [self.game_id],
                            'player_id': [self.player1]},
                           {'game_id': [self.game_id],
                            'player_id': self.player1,
                            'type': 'vote',
                            'vote': self.winner_card}]);
        count += 1
        del self.collected[count][1]['modified']
        looser_card = self.collected[count][0]['card'][0]
        self.assertEquals(self.collected[count],
                          [{'action': ['vote'],
                            'card': [looser_card],
                            'game_id': [self.game_id],
                            'player_id': [self.player2]},
                           {'game_id': [self.game_id],
                            'player_id': self.player2,
                            'type': 'vote',
                            'vote': looser_card}]);
        count += 1
        del self.collected[count][1]['modified']
        self.assertEquals(self.collected[count],
                          [{'action': ['complete'],
                            'game_id': [self.game_id],
                            'owner_id': [self.owner_id]},
                           {'game_id': [self.game_id],
                            'type': 'complete'}]);
        count += 1
        self.assertEqual(len(self.collected), count)

    def test04_poll(self):
        plugin = example.Plugin(self.service, [ AnotherPlugin() ])
        d = plugin.poll({'modified': [plugin.get_modified()]})
        @defer.inlineCallbacks
        def check(result):
            plugin.ok = True
            self.assertEquals(plugin.counter, 1)
            self.assertTrue(result['info'])
            state, players_list = yield plugin.state({'modified': [0]})
            self.assertEquals(plugin.counter, state['counter'])
            defer.returnValue(result)
        d.addCallback(check)
        plugin.count()
        self.assertEquals(plugin.counter, 0)
        return d

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test04_"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(ExampleTest))

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
# compile-command: "python-coverage -e ; PYTHONPATH=../.. python-coverage -x test_example.py ; python-coverage -m -a -r example.py"
# End:
