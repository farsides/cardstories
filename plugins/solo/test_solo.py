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
import sqlite3

from twisted.trial import unittest, runner, reporter
from twisted.internet import reactor, defer

from cardstories.service import CardstoriesService
from plugins.solo.solo import Plugin

class Request:
    
    def __init__(self, **kwargs):
        self.args = kwargs

class SoloTest(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)
        self.service = CardstoriesService({'db': self.database})
        self.service.startService()

    def tearDown(self):
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
        solo = Plugin(self.service, [])
        self.assertEquals(solo.name(), 'solo')
        yield self.complete_game()
        result_in = 'RESULT'
        result_out = yield solo.preprocess(result_in, Request(action = ['game']))
        self.assertEquals(result_in, result_out)

    @defer.inlineCallbacks
    def voting(self, result, player_id):
        d = defer.Deferred()
        def check_voting(event):
            if event and event['type'] == 'change' and event['details']['type'] == 'voting':
                reactor.callLater(0.01, d.callback, True)
            else:
                self.service.listen().addCallback(check_voting)
        card = 111
        yield self.service.pick({ 'action': ['pick'],
                                  'game_id': [result['game_id']],
                                  'player_id': [player_id],
                                  'card': [card] })
        check_voting(None)
        yield d

    @defer.inlineCallbacks
    def complete(self, result, player_id, winner_card):
        d = defer.Deferred()
        def check_complete(event):
            if event and event['type'] == 'change' and event['details']['type'] == 'complete':
                reactor.callLater(0.01, d.callback, True)
            else:
                self.service.listen().addCallback(check_complete)
        card = 111
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [result['game_id']],
                                  'player_id': [player_id],
                                  'card': [winner_card] })
        check_complete(None)
        yield d

    @defer.inlineCallbacks
    def test01_solo(self):
        solo = Plugin(self.service, [])
        yield self.complete_game()
        player_id = 200
        request = Request(action = ['solo'], player_id = [player_id])
        self.assertEquals(len(solo.id2info), 0)
        result = yield solo.preprocess(True, request)
        self.assertEquals(len(solo.id2info), 1)
        self.assertFalse(request.args.has_key('action'))
        self.assertTrue(solo.id2info.has_key(result['game_id']))
        game = self.service.games[result['game_id']]
        game_info = yield game.game(player_id)
        self.assertEquals(game_info['state'], 'invitation')
        yield self.voting(result, player_id)
        yield self.complete(result, player_id, self.winner_card)

    @defer.inlineCallbacks
    def test01_solo_duplicate(self):
        solo = Plugin(self.service, [])
        yield self.complete_game()
        request = Request(action = ['solo'], player_id = [self.player1])
        caught = False
        try:
            yield solo.preprocess(True, request)
        except UserWarning, e:
            caught = True
            self.assertSubstring('tried', e.args[0])
        self.assertTrue(caught)
            
def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(SoloTest))

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
# compile-command: "python-coverage -e ; PYTHONPATH=../.. python-coverage -x test_solo.py ; python-coverage -m -a -r solo.py"
# End:
