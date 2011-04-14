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
import os
sys.path.insert(0, os.path.abspath("..")) # so that for M-x pdb works
import sqlite3

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer, reactor
from twisted.web import server, resource, http

from cardstories.game import CardstoriesGame
from cardstories.service import CardstoriesService

class CardstoriesGameTest(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)
        self.service = CardstoriesService({'db': self.database})
        self.service.startService()
        self.db = sqlite3.connect(self.database)
        self.game = CardstoriesGame(self.service)

    def tearDown(self):
        self.db.close()
        os.unlink(self.database)
        return self.service.stopService()

    @defer.inlineCallbacks
    def test01_create(self):
        #
        # create a game from scratch
        #
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        result = yield self.game.create({ 'card': [card],
                                          'sentence': [sentence],
                                          'owner_id': [owner_id]})
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
        self.assertEquals(self.game.get_players(), [owner_id])
        #
        # load an existing game
        #
        game = CardstoriesGame(self.service, self.game.get_id())
        game.load(c)
        self.assertEquals(game.get_players(), [owner_id])
        c.close()

    @defer.inlineCallbacks
    def test02_participate(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.game.create({ 'card': [card],
                                        'sentence': [sentence],
                                        'owner_id': [owner_id]})
        #
        # assert what happens when a player participates
        #
        c = self.db.cursor()
        c.execute("SELECT LENGTH(cards) FROM games WHERE id = %d" % game['game_id'])
        cards_length = c.fetchone()[0]
        player_id = 23
        self.assertEquals([owner_id], self.game.get_players())
        participation = yield self.game.participate({ 'player_id': [player_id],
                                                         'game_id': [game['game_id']] })
        self.assertEquals([game['game_id']], participation['game_id'])
        self.assertEquals([owner_id, player_id], self.game.get_players())
        c.execute("SELECT LENGTH(cards) FROM games WHERE id = %d" % game['game_id'])
        self.assertEquals(cards_length - self.game.CARDS_PER_PLAYER, c.fetchone()[0])
        c.execute("SELECT LENGTH(cards) FROM player2game WHERE game_id = %d AND player_id = %d" % ( game['game_id'], player_id ))
        self.assertEquals(self.game.CARDS_PER_PLAYER, c.fetchone()[0])
        c.close()
        #
        # assert the difference for when an invited player participates
        #
        invited = 20
        yield self.game.invite({ 'game_id': [game['game_id']],
                                          'player_id': [invited],
                                          'owner_id': [owner_id] })
        self.assertEquals([owner_id, player_id], self.game.players)
        self.assertEquals([invited], self.game.invited)
        participation = yield self.game.participate({ 'player_id': [invited],
                                                      'game_id': [game['game_id']] })
        self.assertEquals([game['game_id']], participation['game_id'])
        self.assertEquals([owner_id, player_id, invited], self.game.players)
        self.assertEquals([], self.game.invited)
        self.assertEquals([owner_id, player_id, invited], self.game.get_players())

    @defer.inlineCallbacks
    def test03_player2game(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.game.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        player_id = 23
        yield self.game.participate({ 'player_id': [player_id],
                                         'game_id': [game['game_id']] })
        player = yield self.game.player2game({ 'player_id': [player_id],
                                                  'game_id': [game['game_id']] })
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(player['cards']))
        self.assertEquals(None, player['vote'])
        self.assertEquals(u'n', player['win'])

    @defer.inlineCallbacks
    def test04_pick(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.game.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        player2card = {}
        for player_id in ( 16, 17 ):
            yield self.game.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.game.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            player2card[player_id] = player['cards'][0]
            yield self.game.pick({ 'player_id': [player_id],
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
        game = yield self.game.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        cards = [card]
        players = [ 16, 17 ]
        for player_id in players:
            yield self.game.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.game.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            card = player['cards'][0]
            cards.append(card)
            yield self.game.pick({ 'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [card] })
        
        invited = 20
        yield self.game.invite({ 'game_id': [game['game_id']],
                                          'player_id': [invited],
                                          'owner_id': [owner_id] })
        self.assertEquals([owner_id] + players + [invited], self.game.get_players())
        yield self.game.voting({ 'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })
        self.assertEquals([], self.game.invited)
        self.assertEquals([owner_id] + players, self.game.get_players())
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
        game = yield self.game.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        for player_id in ( 16, 17 ):
            yield self.game.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.game.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            card = player['cards'][0]
            yield self.game.pick({ 'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [card] })
        
        yield self.game.voting({ 'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })
        
        c = self.db.cursor()
        for player_id in ( owner_id, 16, 17 ):
            vote = 1
            yield self.game.vote({ 'game_id': [game['game_id']],
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
        game = yield self.game.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        for player_id in ( 16, 17 ):
            yield self.game.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.game.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            card = player['cards'][0]
            yield self.game.pick({ 'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [card] })
        
        yield self.game.voting({ 'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })

        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % game['game_id'])
        board = c.fetchone()[0]
        winner_id = 16
        yield self.game.vote({ 'game_id': [game['game_id']],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = 17
        yield self.game.vote({ 'game_id': [game['game_id']],
                                  'player_id': [loser_id],
                                  'card': [120] })
        yield self.game.complete({ 'game_id': [game['game_id']],
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
        game = yield self.game.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})

        # move to invitation state
        player1 = 16
        card1 = 20
        player2 = 17
        card2 = 25
        for player_id in ( player1, player2 ):
            result = yield self.game.participate({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            self.assertEquals([game['game_id']], result['game_id'])

        # invitation state, visitor point of view
        game_info = yield self.game.game({ 'game_id': [game['game_id']] })
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
        game_info = yield self.game.game({ 'game_id': [game['game_id']], 'player_id': [owner_id] })
        self.assertEquals([winner_card], game_info['board'])
        self.assertTrue(winner_card not in game_info['cards'])
        self.assertEquals(self.game.NCARDS, len(game_info['cards']) + sum(map(lambda player: len(player[4]), game_info['players'])))
        self.assertTrue(game_info['owner'])
        self.assertFalse(game_info['ready'])
        self.assertEquals(winner_card, game_info['winner_card'])
        self.assertEquals(game['game_id'], game_info['id'])
        self.assertEquals(owner_id, game_info['players'][0][0])
        self.assertEquals(1, len(game_info['players'][0][4]))
        self.assertEquals(winner_card, game_info['players'][0][3])
        self.assertEquals(player1, game_info['players'][1][0])
        self.assertEquals(None, game_info['players'][1][3])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][1][4]))
        self.assertEquals(player2, game_info['players'][2][0])
        self.assertEquals(None, game_info['players'][2][3])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][2][4]))
        self.assertEquals([winner_card, None, [winner_card]], game_info['self'])
        self.assertEquals(u'SENTENCE', game_info['sentence'])
        self.assertEquals(u'invitation', game_info['state'])

        # players vote
        result = yield self.game.pick({ 'player_id': [player1],
                                           'game_id': [game['game_id']],
                                           'card': [card1] })
        self.assertEquals([game['game_id']], result['game_id'])
        result = yield self.game.pick({ 'player_id': [player2],
                                           'game_id': [game['game_id']],
                                           'card': [card2] })
        self.assertEquals([game['game_id']], result['game_id'])

        # invitation state, owner point of view
        game_info = yield self.game.game({ 'game_id': [game['game_id']], 'player_id': [owner_id] })
        self.assertTrue(game_info['ready'])

        # move to vote state
        result = yield self.game.voting({ 'game_id': [game['game_id']],
                                             'owner_id': [owner_id] })
        self.assertEquals([game['game_id']], result['game_id'])
        # vote state, owner point of view
        game_info = yield self.game.game({ 'game_id': [game['game_id']], 'player_id': [owner_id] })
        self.assertEquals([winner_card, card1, card2], game_info['board'])
        self.assertTrue(winner_card not in game_info['cards'])
        self.assertEquals(self.game.NCARDS, len(game_info['cards']) + sum(map(lambda player: len(player[4]), game_info['players'])))
        self.assertTrue(game_info['owner'])
        self.assertFalse(game_info['ready'])
        self.assertEquals(game['game_id'], game_info['id'])
        self.assertEquals(owner_id, game_info['players'][0][0])
        self.assertEquals(winner_card, game_info['players'][0][3])
        self.assertEquals(1, len(game_info['players'][0][4]))
        self.assertEquals(player1, game_info['players'][1][0])
        self.assertEquals(card1, game_info['players'][1][3])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][1][4]))
        self.assertEquals(player2, game_info['players'][2][0])
        self.assertEquals(card2, game_info['players'][2][3])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][2][4]))
        self.assertEquals([winner_card, None, [winner_card]], game_info['self'])
        self.assertEquals(u'SENTENCE', game_info['sentence'])
        self.assertEquals(u'vote', game_info['state'])

        # every player vote
        result = yield self.game.vote({ 'game_id': [game['game_id']],
                                           'player_id': [player1],
                                           'card': [card2] })
        self.assertEquals([game['game_id']], result['game_id'])
        result = yield self.game.vote({ 'game_id': [game['game_id']],
                                           'player_id': [player2],
                                           'card': [card1] })
        self.assertEquals([game['game_id']], result['game_id'])
        # vote state, player point of view
        game_info = yield self.game.game({ 'game_id': [game['game_id']], 'player_id': [player1] })
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
        #
        # create a game and invite players
        #
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        invited = [20,21]
        game = yield self.game.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        self.assertEquals([owner_id], self.game.get_players())
        result = yield self.game.invite({ 'game_id': [game['game_id']],
                                             'player_id': invited,
                                             'owner_id': [owner_id] })
        self.assertEquals([game['game_id']], result['game_id'])
        self.assertEquals(invited, self.game.invited)
        self.assertEquals([owner_id] + invited, self.game.get_players())
        c = self.db.cursor()
        c.execute("SELECT * FROM invitations WHERE game_id = %d" % game['game_id'])
        self.assertEquals(c.fetchall(), [(invited[0], game['game_id']),
                                         (invited[1], game['game_id'])])
        #
        # load an existing game, invitations included
        #
        other_game = CardstoriesGame(self.service, self.game.get_id())
        other_game.load(c)
        self.assertEquals(other_game.get_players(), [owner_id] + invited)
        participation = yield self.game.participate({ 'player_id': [invited[0]],
                                                         'game_id': [game['game_id']] })
        self.assertEquals([game['game_id']], result['game_id'])
        c.execute("SELECT * FROM invitations WHERE game_id = %d" % game['game_id'])
        self.assertEquals(c.fetchall(), [(invited[1], game['game_id'])])
        yield self.game.voting({ 'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })
        c.execute("SELECT * FROM invitations WHERE game_id = %d" % game['game_id'])
        self.assertEquals(c.fetchall(), [])
        c.close()

    @defer.inlineCallbacks
    def test10_touch(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.game.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        result = self.game.touch()
        self.assertEquals([game['game_id']], result['game_id'])
        self.assertEquals(self.game.modified, result['modified'][0])
        
def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test10_"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesGameTest))

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
# compile-command: "python-coverage -e ; PYTHONPATH=.. python-coverage -x test_game.py ; python-coverage -m -a -r ../cardstories/game.py"
# End:
