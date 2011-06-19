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
import sys
import os
sys.path.insert(0, os.path.abspath("../..")) # so that for M-x pdb works

from twisted.trial import unittest, runner, reporter
from twisted.internet import reactor, defer

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

        
class ExampleTest(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)
        self.service = CardstoriesService({'db': self.database,
                                           'plugins-confdir': 'CONFDIR',
                                           'plugins-libdir': 'LIBDIR'
                                           })

    @defer.inlineCallbacks
    def complete_game(self):
        self.winner_card = winner_card = 5
        self.player1 = 1001
        self.player2 = 1002
        self.owner_id = 1003
        sentence = 'SENTENCE'
        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [self.owner_id]})
        self.game_id = game['game_id']
        yield self.service.invite({ 'action': ['invite'],
                                    'game_id': [self.game_id],
                                    'player_id': [self.player1],
                                    'owner_id': [self.owner_id] })
        for player_id in ( self.player1, self.player2 ):
            yield self.service.participate({ 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [self.game_id] })
            player = yield self.service.player2game({ 'action': ['player2game'],
                                                      'player_id': [player_id],
                                                      'game_id': [self.game_id] })
            card = player['cards'][0]
            yield self.service.pick({ 'action': ['pick'],
                                      'player_id': [player_id],
                                      'game_id': [self.game_id],
                                      'card': [card] })
        
        yield self.service.voting({ 'action': ['voting'],
                                    'game_id': [self.game_id],
                                    'owner_id': [self.owner_id] })
        winner_id = self.player1
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [self.game_id],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = self.player2
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [self.game_id],
                                  'player_id': [loser_id],
                                  'card': [120] })
        self.assertTrue(self.service.games.has_key(self.game_id))
        yield self.service.complete({ 'action': ['complete'],
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
        yield self.complete_game()
        yield self.service.stopService()
        self.assertEqual(self.events, ['START',
                                       'CHANGE init',
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

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
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
