#
# Copyright (C) 2011 Dachary <loic@dachary.org>
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
sys.path.insert(0, "..") # so that for M-x pdb works
import os
import sqlite3

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer, reactor
from twisted.web import server, resource, http

from cardstories.service import CardstoriesService

class CardstoriesServiceTestInit(unittest.TestCase):

    def test00_startService(self):
        database = 'test.sqlite'
        service = CardstoriesService({'db': database})
        self.assertFalse(os.path.exists(database))
        service.startService()
        self.assertTrue(os.path.exists(database))

class CardstoriesServiceTest(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)
        self.service = CardstoriesService({'db': self.database})
        self.service.startService()
        self.db = sqlite3.connect(self.database)

    def tearDown(self):
        self.db.close()
        os.unlink(self.database)

class CardstoriesServiceTestRun(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)

    def tearDown(self):
        os.unlink(self.database)

    def test00_run(self):
        self.service = CardstoriesService({'db': self.database, 'loop': 2, 'click': 0.1})
        d = self.service.startService()
        d.addCallback(lambda result: self.assertTrue(result))
        return d

class CardstoriesServiceTestHandle(CardstoriesServiceTest):

    def test01_required(self):
        self.assertTrue(CardstoriesService.required({ 'key1': ['a'],
                                                      'key2': ['b'] }, 'method', 'key1'))
        
        self.failUnlessRaises(UserWarning, CardstoriesService.required, { }, 'method', 'key1')

    @defer.inlineCallbacks
    def test02_handle(self):
        for action in self.service.ACTIONS:
            result = yield self.service.handle({ 'action': [action] })
            self.failUnlessSubstring(action, result['error'])
            self.failUnlessSubstring('must be given', result['error'])

class CardstoriesServiceTest(CardstoriesServiceTest):

    def test01_create(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        d = self.service.create({ 'card': [card],
                                  'sentence': [sentence],
                                  'owner_id': [owner_id]})
        def check(result):
            c = self.db.cursor()
            c.execute("SELECT * FROM games")
            rows = c.fetchall()
            self.assertEquals(1, len(rows))
            self.assertEquals(result['game_id'], rows[0][0])
            self.assertEquals(owner_id, rows[0][1])
            one_player = 1
            self.assertEquals(one_player, rows[0][2])
            self.assertEquals(sentence, rows[0][3])
            self.assertFalse(chr(card) in rows[0][4])
            self.assertEquals(chr(card), rows[0][5])
            c.execute("SELECT cards FROM player2game WHERE game_id = %d AND player_id = %d" %  ( result['game_id'], owner_id ))
            rows = c.fetchall()
            self.assertEquals(1, len(rows))
            self.assertEquals(chr(card), rows[0][0])
            c.close()
        d.addCallback(check)
        return d

    @defer.inlineCallbacks
    def test02_participate(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        c = self.db.cursor()
        c.execute("SELECT LENGTH(cards) FROM games WHERE id = %d" % game['game_id'])
        cards_length = c.fetchone()[0]
        player_id = 23
        participation = yield self.service.participate({ 'player_id': [player_id],
                                                         'game_id': [game['game_id']] })
        self.assertEquals({}, participation)
        c.execute("SELECT LENGTH(cards) FROM games WHERE id = %d" % game['game_id'])
        self.assertEquals(cards_length - self.service.CARDS_PER_PLAYER, c.fetchone()[0])
        c.execute("SELECT LENGTH(cards) FROM player2game WHERE game_id = %d AND player_id = %d" % ( game['game_id'], player_id ))
        self.assertEquals(self.service.CARDS_PER_PLAYER, c.fetchone()[0])
        c.close()

    @defer.inlineCallbacks
    def test03_player2game(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        player_id = 23
        yield self.service.participate({ 'player_id': [player_id],
                                         'game_id': [game['game_id']] })
        player = yield self.service.player2game({ 'player_id': [player_id],
                                                  'game_id': [game['game_id']] })
        self.assertEquals(self.service.CARDS_PER_PLAYER, len(player['cards']))
        self.assertEquals(None, player['vote'])
        self.assertEquals(u'n', player['win'])

    @defer.inlineCallbacks
    def test04_pick(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        player2card = {}
        for player_id in ( 16, 17 ):
            yield self.service.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.service.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            player2card[player_id] = player['cards'][0]
            yield self.service.pick({ 'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [ player2card[player_id] ] })
        
        c = self.db.cursor()
        for player_id in ( 16, 17 ):
            c.execute("SELECT picked FROM player2game WHERE game_id = %d AND player_id = %d" % ( game['game_id'], player_id ))
            self.assertEquals(player2card[player_id], ord(c.fetchone()[0]))
        c.close()
            
    @defer.inlineCallbacks
    def test05_state_vote(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        cards = [card]
        for player_id in ( 16, 17 ):
            yield self.service.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.service.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            card = player['cards'][0]
            cards.append(card)
            yield self.service.pick({ 'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [card] })
        
        yield self.service.voting({ 'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })
        c = self.db.cursor()
        c.execute("SELECT board, state FROM games WHERE id = %d" % ( game['game_id'] ))
        row = c.fetchone()
        board = map(lambda c: ord(c), row[0])
        board.sort()
        cards.sort()
        self.assertEquals(board, cards)
        self.assertEquals(u'vote', row[1])
        c.close()

    @defer.inlineCallbacks
    def test06_vote(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        for player_id in ( 16, 17 ):
            yield self.service.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.service.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            card = player['cards'][0]
            yield self.service.pick({ 'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [card] })
        
        yield self.service.voting({ 'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })
        
        c = self.db.cursor()
        for player_id in ( owner_id, 16, 17 ):
            vote = 1
            yield self.service.vote({ 'game_id': [game['game_id']],
                                      'player_id': [player_id],
                                      'card': [vote] })
            c.execute("SELECT vote FROM player2game WHERE game_id = %d AND player_id = %d" % ( game['game_id'], player_id ))
            self.assertEqual(chr(vote), c.fetchone()[0])
        c.close()
            
    @defer.inlineCallbacks
    def test07_complete(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        for player_id in ( 16, 17 ):
            yield self.service.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.service.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            card = player['cards'][0]
            yield self.service.pick({ 'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [card] })
        
        yield self.service.voting({ 'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })

        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % game['game_id'])
        board = c.fetchone()[0]
        winner_id = 16
        yield self.service.vote({ 'game_id': [game['game_id']],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = 17
        yield self.service.vote({ 'game_id': [game['game_id']],
                                  'player_id': [loser_id],
                                  'card': [120] })
        yield self.service.complete({ 'game_id': [game['game_id']],
                                      'owner_id': [owner_id] })
        c.execute("SELECT win FROM player2game WHERE game_id = %d AND player_id IN ( %d, %d )" % ( game['game_id'], winner_id, owner_id ))
        self.assertEqual(u'y', c.fetchone()[0])
        self.assertEqual(u'y', c.fetchone()[0])
        c.close()
            
    @defer.inlineCallbacks
    def test08_game(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})

        # move to invitation state
        player1 = 16
        card1 = 20
        player2 = 17
        card2 = 25
        for player_id in ( player1, player2 ):
            result = yield self.service.participate({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            self.assertEquals(result, {})

        # invitation state, visitor point of view
        game_info = yield self.service.game({ 'game_id': [game['game_id']] })
        self.assertEquals({'board': None,
                           'cards': None,
                           'id': game['game_id'],
                           'ready': False,
                           'owner': False,
                           'players': [[owner_id, None, u'n', None, None], [player1, None, u'n', None, None], [player2, None, u'n', None, None]],
                           'self': None,
                           'sentence': u'SENTENCE',
                           'winner_card': None,
                           'state': u'invitation'}, game_info)
        
        # invitation state, owner point of view
        game_info = yield self.service.game({ 'game_id': [game['game_id']], 'player_id': [owner_id] })
        self.assertEquals([winner_card], game_info['board'])
        self.assertTrue(winner_card not in game_info['cards'])
        self.assertEquals(self.service.NCARDS, len(game_info['cards']) + sum(map(lambda player: len(player[4]), game_info['players'])))
        self.assertTrue(game_info['owner'])
        self.assertFalse(game_info['ready'])
        self.assertEquals(winner_card, game_info['winner_card'])
        self.assertEquals(game['game_id'], game_info['id'])
        self.assertEquals(owner_id, game_info['players'][0][0])
        self.assertEquals(1, len(game_info['players'][0][4]))
        self.assertEquals(winner_card, game_info['players'][0][3])
        self.assertEquals(player1, game_info['players'][1][0])
        self.assertEquals(None, game_info['players'][1][3])
        self.assertEquals(self.service.CARDS_PER_PLAYER, len(game_info['players'][1][4]))
        self.assertEquals(player2, game_info['players'][2][0])
        self.assertEquals(None, game_info['players'][2][3])
        self.assertEquals(self.service.CARDS_PER_PLAYER, len(game_info['players'][2][4]))
        self.assertEquals([winner_card, None, [winner_card]], game_info['self'])
        self.assertEquals(u'SENTENCE', game_info['sentence'])
        self.assertEquals(u'invitation', game_info['state'])

        # players vote
        result = yield self.service.pick({ 'player_id': [player1],
                                           'game_id': [game['game_id']],
                                           'card': [card1] })
        self.assertEquals(result, {})
        result = yield self.service.pick({ 'player_id': [player2],
                                           'game_id': [game['game_id']],
                                           'card': [card2] })
        self.assertEquals(result, {})

        # invitation state, owner point of view
        game_info = yield self.service.game({ 'game_id': [game['game_id']], 'player_id': [owner_id] })
        self.assertTrue(game_info['ready'])

        # move to vote state
        result = yield self.service.voting({ 'game_id': [game['game_id']],
                                             'owner_id': [owner_id] })
        self.assertEquals(result, {})
        # vote state, owner point of view
        game_info = yield self.service.game({ 'game_id': [game['game_id']], 'player_id': [owner_id] })
        self.assertEquals([winner_card, card1, card2], game_info['board'])
        self.assertTrue(winner_card not in game_info['cards'])
        self.assertEquals(self.service.NCARDS, len(game_info['cards']) + sum(map(lambda player: len(player[4]), game_info['players'])))
        self.assertTrue(game_info['owner'])
        self.assertFalse(game_info['ready'])
        self.assertEquals(game['game_id'], game_info['id'])
        self.assertEquals(owner_id, game_info['players'][0][0])
        self.assertEquals(winner_card, game_info['players'][0][3])
        self.assertEquals(1, len(game_info['players'][0][4]))
        self.assertEquals(player1, game_info['players'][1][0])
        self.assertEquals(card1, game_info['players'][1][3])
        self.assertEquals(self.service.CARDS_PER_PLAYER, len(game_info['players'][1][4]))
        self.assertEquals(player2, game_info['players'][2][0])
        self.assertEquals(card2, game_info['players'][2][3])
        self.assertEquals(self.service.CARDS_PER_PLAYER, len(game_info['players'][2][4]))
        self.assertEquals([winner_card, None, [winner_card]], game_info['self'])
        self.assertEquals(u'SENTENCE', game_info['sentence'])
        self.assertEquals(u'vote', game_info['state'])

        # every player vote
        result = yield self.service.vote({ 'game_id': [game['game_id']],
                                           'player_id': [player1],
                                           'card': [card2] })
        self.assertEquals(result, {})
        result = yield self.service.vote({ 'game_id': [game['game_id']],
                                           'player_id': [player2],
                                           'card': [card1] })
        self.assertEquals(result, {})
        # vote state, player point of view
        game_info = yield self.service.game({ 'game_id': [game['game_id']], 'player_id': [player1] })
        player1_cards = game_info['players'][1][4]
        self.assertEquals({'board': [winner_card, card1, card2],
                           'cards': None,
                           'id': game['game_id'],
                           'ready': True,
                           'owner': False,
                           'players': [[owner_id, None, u'n', None, None], [player1, None, u'n', card1, player1_cards], [player2, None, u'n', None, None]],
                           'self': [card1, card2, player1_cards],
                           'sentence': u'SENTENCE',
                           'winner_card': None,
                           'state': u'vote'}, game_info)
        # move to complete state

    @defer.inlineCallbacks
    def test09_invitation(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        invited = [20,21]
        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        result = yield self.service.invite({ 'game_id': [game['game_id']],
                                             'player_id': invited,
                                             'owner_id': [owner_id] })
        self.assertEquals(result, {})
        c = self.db.cursor()
        c.execute("SELECT * FROM invitations WHERE game_id = %d" % game['game_id'])
        self.assertEquals(c.fetchall(), [(invited[0], game['game_id']),
                                         (invited[1], game['game_id'])])
        participation = yield self.service.participate({ 'player_id': [invited[0]],
                                                         'game_id': [game['game_id']] })
        self.assertEquals({}, participation)
        c.execute("SELECT * FROM invitations WHERE game_id = %d" % game['game_id'])
        self.assertEquals(c.fetchall(), [(invited[1], game['game_id'])])
        yield self.service.voting({ 'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })
        c.execute("SELECT * FROM invitations WHERE game_id = %d" % game['game_id'])
        self.assertEquals(c.fetchall(), [])
        c.close()
        
def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesServiceTestInit))
    suite.addTest(loader.loadClass(CardstoriesServiceTest))
    suite.addTest(loader.loadClass(CardstoriesServiceTestHandle))
    suite.addTest(loader.loadClass(CardstoriesServiceTestRun))

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
# compile-command: "python-coverage -e ; PYTHONPATH=.. python-coverage -x test_service.py ; python-coverage -m -a -r ../cardstories/service.py"
# End:
