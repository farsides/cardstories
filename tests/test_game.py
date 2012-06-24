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
sys.path.insert(0, os.path.abspath("..")) # so that for M-x pdb works
import sqlite3
import time

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer

from cardstories.game import CardstoriesGame
from cardstories.service import CardstoriesService
from cardstories.exceptions import CardstoriesWarning

from twisted.internet import base
base.DelayedCall.debug = True

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
        self.game.destroy()
        self.db.close()
        os.unlink(self.database)
        return self.service.stopService()

    @defer.inlineCallbacks
    def create_game(self, owner_id, sentence):
        """Helper function that creates the game, sets the card,
        and sets the sentence in one step.
        Returns the created game's id and the card that was set."""
        game_id = yield self.game.create(owner_id)
        owner = yield self.game.player2game(owner_id)
        card = owner['cards'][0]
        yield self.game.set_card(owner_id, card)
        yield self.game.set_sentence(owner_id, sentence)
        retval = (game_id, card)
        defer.returnValue(retval)

    @defer.inlineCallbacks
    def test01_create(self):
        #
        # create a game from scratch
        #
        owner_id = 15
        game_id = yield self.game.create(owner_id)
        c = self.db.cursor()
        c.execute("SELECT * FROM games")
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        self.assertEquals(game_id, rows[0][0])
        self.assertEquals(owner_id, rows[0][1])
        one_player = 1
        self.assertEquals(one_player, rows[0][2])
        self.assertEquals(None, rows[0][3])
        games_cards = rows[0][4]
        self.assertNotEquals('', games_cards)
        self.assertEquals(len(games_cards), self.game.CARDS_PER_PLAYER)
        self.assertEquals('', rows[0][5])
        self.assertEquals('create', rows[0][6])
        c.execute("SELECT cards FROM player2game WHERE game_id = %d AND player_id = %d" % (game_id, owner_id))
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        player2game_cards = rows[0][0]
        self.assertNotEquals('', player2game_cards)
        self.assertEquals(len(player2game_cards), self.game.CARDS_PER_PLAYER)
        self.assertEquals(games_cards, player2game_cards)
        self.assertEquals(self.game.get_players(), [owner_id])
        self.assertEquals(self.game.get_owner_id(), owner_id)
        c.execute("SELECT player_id FROM players WHERE player_id = %s" % owner_id)
        self.assertEquals(c.fetchone()[0], owner_id)
        #
        # load an existing game
        #
        game = CardstoriesGame(self.service, self.game.get_id())
        game.load(c)
        self.assertEquals(game.get_players(), [owner_id])
        self.assertEquals(self.game.get_owner_id(), owner_id)
        game.destroy()
        c.close()

    @defer.inlineCallbacks
    def test01_set_card(self):
        owner_id = 25
        game_id = yield self.game.create(owner_id)
        owner = yield self.game.player2game(owner_id)
        card = owner['cards'][0]
        yield self.game.set_card(owner_id, card)
        c = self.db.cursor()
        c.execute("SELECT * FROM games")
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        self.assertEquals('create', rows[0][6])
        one_player = 1
        self.assertEquals(one_player, rows[0][2])
        self.assertNotEquals('', rows[0][4])
        self.assertTrue(chr(card) in rows[0][4])
        self.assertEquals(chr(card), rows[0][5])
        c.execute("SELECT picked FROM player2game WHERE game_id = %d AND player_id = %d" % (game_id, owner_id))
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        self.assertEquals(chr(card), rows[0][0])
        c.close()

    @defer.inlineCallbacks
    def test01_set_card_security(self):
        card = 5
        owner_id = 25
        other_player_id = 26
        game_id = yield self.game.create(owner_id)
        #
        # Only owner can set the card.
        #
        self.raised = False
        try:
            yield self.game.set_card(other_player_id, card)
        except Exception:
            self.raised = True
        self.assertTrue(self.raised)

        c = self.db.cursor()
        c.execute("SELECT * FROM games")
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        self.assertEquals('create', rows[0][6])
        one_player = 1
        self.assertEquals(one_player, rows[0][2])
        self.assertNotEquals('', rows[0][4])
        self.assertEquals('', rows[0][5])
        c.execute("SELECT picked FROM player2game WHERE game_id = %d AND player_id = %d" % (game_id, owner_id))
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        self.assertEquals(None, rows[0][0])
        c.close()

    @defer.inlineCallbacks
    def test01_set_card_deal_cards(self):
        the_card = 5
        the_sentence = 'SENTENCE!'
        owner = 12
        player1 = 25
        player2 = 26
        player3 = 27
        player4 = 28
        # Create the game.
        game_id = yield self.game.create(owner)

        # Let players 1 & 2 join the game before the card is set.
        yield self.game.participate(player1)
        yield self.game.participate(player2)

        def check_cards_set(player):
            game_info, player_ids = yield self.game.game(player)
            cards = game_info['self'][2]
            self.assertEquals(len(cards), CardstoriesGame.CARDS_PER_PLAYER)

        # Players 1 and 2 should have been dealt cards already.
        for player in [player1, player2]:
            check_cards_set(player)

        # Set the card.
        yield self.game.set_card(owner, the_card)

        # Let player 3 join now, his cards should be set upon joining.
        yield self.game.participate(player3)
        check_cards_set(player3)

        # Set the sentence, the game will move into 'invitation' state.
        yield self.game.set_sentence(owner, the_sentence)
        game_info, player_ids = yield self.game.game(owner)
        self.assertEquals(game_info['state'], 'invitation')

        # Let player 4 join now. His cards should be set upon joining, too.
        yield self.game.participate(player4)
        check_cards_set(player4)

        # Make a sanity check on player's cards - they should all be unique
        # among each other.
        all_cards = []
        for player in [owner, player1, player2, player3, player4]:
            game_info, player_ids = yield self.game.game(player)
            cards = game_info['self'][2]
            all_cards.extend(cards)
        all_cards = set(all_cards)
        self.assertEquals(len(all_cards), 5 * CardstoriesGame.CARDS_PER_PLAYER)

        # Also, all dealt cards should be stored appropriately.
        c = self.db.cursor()
        c.execute("SELECT cards FROM games WHERE id = ?", [ game_id ])
        game_cards = c.fetchone()[0]
        c.close()
        self.assertEquals(len(game_cards), 5 * CardstoriesGame.CARDS_PER_PLAYER)
        for card in all_cards:
            self.assertTrue(chr(card) in game_cards)


    @defer.inlineCallbacks
    def test01_set_sentence(self):
        card = 5
        sentence = u'SENTENCE \xe9'
        owner_id = 35
        game_id = yield self.game.create(owner_id)
        yield self.game.set_card(owner_id, card)
        yield self.game.set_sentence(owner_id, sentence)
        c = self.db.cursor()
        c.execute("SELECT * FROM games")
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        one_player = 1
        self.assertEquals(one_player, rows[0][2])
        self.assertEquals(sentence, rows[0][3])
        c.close()

    @defer.inlineCallbacks
    def test01_set_sentence_security(self):
        sentence = u'SENTENCE \xe9'
        owner_id = 35
        other_player_id = 36
        game_id = yield self.game.create(owner_id)
        owner = yield self.game.player2game(owner_id)
        card = owner['cards'][0]
        #
        # Cannot set sentence before the card.
        #
        self.raised = False
        try:
            yield self.game.set_sentence(owner_id, sentence)
        except Exception:
            self.raised = True
        self.assertTrue(self.raised)

        yield self.game.set_card(owner_id, card)
        #
        # Only owner can set the sentence.
        #
        self.raised = False
        try:
            yield self.game.set_sentence(other_player_id, sentence)
        except Exception:
            self.raised = True
        self.assertTrue(self.raised)

        c = self.db.cursor()
        c.execute("SELECT * FROM games")
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        self.assertEquals(None, rows[0][3])

        #
        # Cannot only set sentence in 'create' state.
        #
        # Set the sentence, moving the game into 'invitation' state.
        yield self.game.set_sentence(owner_id, sentence)
        self.raised = False
        try:
            other_sentence = 'OTHER SENTENCE'
            yield self.game.set_sentence(owner_id, other_sentence)
        except Exception:
            self.raised = True
        self.assertTrue(self.raised)


        c = self.db.cursor()
        c.execute("SELECT * FROM games")
        rows = c.fetchall()
        self.assertEquals(sentence, rows[0][3])
        c.close()

    @defer.inlineCallbacks
    def test02_participate(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, card = yield self.create_game(owner_id, sentence)
        #
        # assert what happens when a player participates
        #
        c = self.db.cursor()
        c.execute("SELECT LENGTH(cards) FROM games WHERE id = %d" % game_id)
        cards_length = c.fetchone()[0]
        player_id = 23
        self.assertEquals([owner_id], self.game.get_players())
        participation = yield self.game.participate(player_id)
        self.assertEquals([game_id], participation['game_id'])
        self.assertEquals('participate', participation['type'])
        self.assertEquals(player_id, participation['player_id'])
        self.assertEquals([owner_id, player_id], self.game.get_players())
        c.execute("SELECT LENGTH(cards) FROM games WHERE id = %d" % game_id)
        self.assertEquals(cards_length + self.game.CARDS_PER_PLAYER, c.fetchone()[0])
        c.execute("SELECT LENGTH(cards) FROM player2game WHERE game_id = %d AND player_id = %d" % (game_id, player_id))
        self.assertEquals(self.game.CARDS_PER_PLAYER, c.fetchone()[0])
        c.execute("SELECT player_id FROM players WHERE player_id = %s" % player_id)
        self.assertEquals(c.fetchone()[0], player_id)
        c.close()
        #
        # assert the difference for when an invited player participates
        #
        invited = 20
        yield self.game.invite([invited])
        self.assertEquals([owner_id, player_id], self.game.players)
        self.assertEquals([invited], self.game.invited)
        participation = yield self.game.participate(invited)
        self.assertEquals([game_id], participation['game_id'])
        self.assertEquals([owner_id, player_id, invited], self.game.players)
        self.assertEquals([], self.game.invited)
        self.assertEquals([owner_id, player_id, invited], self.game.get_players())
        #
        # assert exception is raised when game is full
        #
        player_id = 30
        while len(self.game.players) < self.game.NPLAYERS:
            yield self.game.participate(player_id)
            player_id += 1
        # The game is full, trying to add another player should raise an exception.
        raises_CardstoriesException = False
        error_code = None
        error_data = {}
        try:
            yield self.game.participate(player_id)
        except CardstoriesWarning as e:
            raises_CardstoriesException = True
            error_code = e.code
            error_data = e.data
        self.assertTrue(raises_CardstoriesException)
        self.assertEquals('GAME_FULL', error_code)
        self.assertEquals(self.game.NPLAYERS, error_data['max_players'])

    @defer.inlineCallbacks
    def test03_player2game(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, card = yield self.create_game(owner_id, sentence)
        player_id = 23
        yield self.game.participate(player_id)
        player = yield self.game.player2game(player_id)
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(player['cards']))
        self.assertEquals(None, player['vote'])
        self.assertEquals(u'n', player['win'])

    @defer.inlineCallbacks
    def test04_pick(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, card = yield self.create_game(owner_id, sentence)
        player2card = {}
        for player_id in (16, 17):
            yield self.game.participate(player_id)
            player = yield self.game.player2game(player_id)
            player2card[player_id] = player['cards'][0]
            result = yield self.game.pick(player_id, player2card[player_id])
            self.assertEquals(result['type'], 'pick')
            self.assertEquals(result['player_id'], player_id)
            self.assertEquals(result['card'], player2card[player_id])
        
        c = self.db.cursor()
        for player_id in (16, 17):
            c.execute("SELECT picked FROM player2game WHERE game_id = %d AND player_id = %d" % (game_id, player_id))
            self.assertEquals(player2card[player_id], ord(c.fetchone()[0]))
        c.close()
            
    @defer.inlineCallbacks
    def test05_state_vote(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, card = yield self.create_game(owner_id, sentence)
        cards = [card]
        pick_players = [ 16, 17 ]
        players = pick_players + [ 18 ]
        for player_id in players:
            yield self.game.participate(player_id)
        for player_id in pick_players:
            player = yield self.game.player2game(player_id)
            card = player['cards'][0]
            cards.append(card)
            yield self.game.pick(player_id, card)
        invited = 20
        yield self.game.invite([invited])
        self.assertEquals([owner_id] + players + [invited], self.game.get_players())
        result = yield self.game.voting(owner_id)
        self.assertEquals(result['type'], 'voting')
        self.assertEquals([], self.game.invited)
        self.assertEquals([owner_id] + pick_players, self.game.get_players())
        c = self.db.cursor()
        c.execute("SELECT board, state FROM games WHERE id = %d" % (game_id))
        row = c.fetchone()
        board = map(lambda c: ord(c), row[0])
        board.sort()
        cards.sort()
        self.assertEquals(board, cards)
        self.assertEquals(u'vote', row[1])
        c.close()

    @defer.inlineCallbacks
    def test06_vote(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, card = yield self.create_game(owner_id, sentence)
        for player_id in (16, 17):
            yield self.game.participate(player_id)
            player = yield self.game.player2game(player_id)
            card = player['cards'][0]
            yield self.game.pick(player_id, card)

        yield self.game.voting(owner_id)
        
        c = self.db.cursor()
        for player_id in (owner_id, 16, 17):
            vote = 1
            result = yield self.game.vote(player_id, vote)
            self.assertEquals(result['type'], 'vote')
            self.assertEquals(result['player_id'], player_id)
            self.assertEquals(result['vote'], vote)
            c.execute("SELECT vote FROM player2game WHERE game_id = %d AND player_id = %d" % (game_id, player_id))
            self.assertEqual(chr(vote), c.fetchone()[0])
        c.close()
            
    @defer.inlineCallbacks
    def test07_complete(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, winner_card = yield self.create_game(owner_id, sentence)
        player1_id = 16
        player2_id = 17
        player3_id = 18
        voting_players = [ player1_id, player2_id ]
        players = voting_players + [ player3_id ]
        for player_id in players:
            yield self.game.participate(player_id)
            player = yield self.game.player2game(player_id)
            card = player['cards'][0]
            yield self.game.pick(player_id, card)
        yield self.game.voting(owner_id)

        # Owner wins, player1 wins, and player2 loses
        yield self.game.vote(player1_id, winner_card)
        yield self.game.vote(player2_id, 120)
        self.assertEquals(self.game.get_players(), [owner_id] + players)

        # Move the game to the complete state, but add a poll so we can get
        # game info before it's destroyed.
        poll_game = self.game
        @defer.inlineCallbacks
        def get_infos(result):
            owner_info = yield poll_game.game(owner_id)
            player1_info = yield poll_game.game(player1_id)
            player2_info = yield poll_game.game(player2_id)
            defer.returnValue({'owner': owner_info,
                               'player1': player1_info,
                               'player2': player2_info})
        gameinfo_poll = self.game.poll({'modified':[self.game.get_modified()]})
        gameinfo_poll.addCallback(get_infos)
        result = yield self.game.complete(owner_id)
        game_infos = yield gameinfo_poll
        self.assertEquals(result['type'], 'complete')
        self.assertEquals(self.game.get_players(), [owner_id] + players)
        c = self.db.cursor()
        c.execute("SELECT win, vote FROM player2game WHERE game_id = %d AND player_id != %d" % (game_id, owner_id))
        self.assertEqual((u'y', chr(winner_card)), c.fetchone())
        self.assertEqual(u'n', c.fetchone()[0])
        self.assertEqual((u'n', None), c.fetchone())
        self.assertEqual(c.fetchone(), None)
        c.close()

        # Score, owner point of view
        pinfo = game_infos['owner'][0]['players'][0]
        self.assertEquals('y', pinfo['win'])
        self.assertEquals(12, pinfo['score'])
        self.assertEquals(2, pinfo['level'])
        self.assertEquals(17, pinfo['score_next'])
        self.assertEquals(6, pinfo['score_left'])
        self.assertEquals(0, pinfo['score_prev'])
        self.assertEquals(1, pinfo['level_prev'])
        self.assertEquals(1, len(pinfo['earned_cards']))
        self.assertEquals(1, len(pinfo['earned_cards_cur']))

        # Score, player1 point of view
        pinfo = game_infos['player1'][0]['players'][1]
        self.assertEquals('y', pinfo['win'])
        self.assertEquals(5, pinfo['score'])
        self.assertEquals(2, pinfo['level'])
        self.assertEquals(17, pinfo['score_next'])
        self.assertEquals(13, pinfo['score_left'])
        self.assertEquals(0, pinfo['score_prev'])
        self.assertEquals(1, pinfo['level_prev'])
        self.assertEquals(1, len(pinfo['earned_cards']))
        self.assertEquals(1, len(pinfo['earned_cards_cur']))

        # Score, player2 point of view
        pinfo = game_infos['player2'][0]['players'][2]
        self.assertEquals('n', pinfo['win'])
        self.assertEquals(1, pinfo['score'])
        self.assertEquals(2, pinfo['level'])
        self.assertEquals(17, pinfo['score_next'])
        self.assertEquals(17, pinfo['score_left'])
        self.assertEquals(0, pinfo['score_prev'])
        self.assertEquals(1, pinfo['level_prev'])
        self.assertEquals(1, len(pinfo['earned_cards']))
        self.assertEquals(1, len(pinfo['earned_cards_cur']))

        # Play another game to check the score difference.
        other_game = CardstoriesGame(self.service)
        other_game_id = yield other_game.create(owner_id)
        owner = yield other_game.player2game(owner_id)
        winner_card = owner['cards'][0]
        yield other_game.set_card(owner_id, winner_card)
        yield other_game.set_sentence(owner_id, sentence)
        for player_id in players:
            yield other_game.participate(player_id)
            player = yield other_game.player2game(player_id)
            card = player['cards'][0]
            yield other_game.pick(player_id, card)
        yield other_game.voting(owner_id)
        # This time, owner wins again but player1 loses, and player2 wins
        yield other_game.vote(player1_id, 120)
        yield other_game.vote(player2_id, winner_card)
        gameinfo_poll = other_game.poll({'modified':[other_game.get_modified()]})
        poll_game = other_game
        gameinfo_poll.addCallback(get_infos)
        yield other_game.complete(owner_id)
        game_infos = yield gameinfo_poll

        # Score, owner point of view
        pinfo = game_infos['owner'][0]['players'][0]
        self.assertEquals('y', pinfo['win'])
        self.assertEquals(24, pinfo['score'])
        self.assertEquals(3, pinfo['level'])
        self.assertEquals(38, pinfo['score_next'])
        self.assertEquals(32, pinfo['score_left'])
        self.assertEquals(12, pinfo['score_prev'])
        self.assertEquals(2, pinfo['level_prev'])
        self.assertEquals(2, len(pinfo['earned_cards']))
        self.assertEquals(1, len(pinfo['earned_cards_cur']))

        # Score, player1 point of view
        pinfo = game_infos['player1'][0]['players'][1]
        self.assertEquals('n', pinfo['win'])
        self.assertEquals(6, pinfo['score'])
        self.assertEquals(2, pinfo['level'])
        self.assertEquals(17, pinfo['score_next'])
        self.assertEquals(12, pinfo['score_left'])
        self.assertEquals(5, pinfo['score_prev'])
        self.assertEquals(2, pinfo['level_prev'])
        self.assertEquals(1, len(pinfo['earned_cards']))
        self.assertEquals(None, pinfo['earned_cards_cur'])

        # Score, player2 point of view
        pinfo = game_infos['player2'][0]['players'][2]
        self.assertEquals('y', pinfo['win'])
        self.assertEquals(6, pinfo['score'])
        self.assertEquals(2, pinfo['level'])
        self.assertEquals(17, pinfo['score_next'])
        self.assertEquals(12, pinfo['score_left'])
        self.assertEquals(1, pinfo['score_prev'])
        self.assertEquals(2, pinfo['level_prev'])
        self.assertEquals(1, len(pinfo['earned_cards']))
        self.assertEquals(None, pinfo['earned_cards_cur'])
            
    @defer.inlineCallbacks
    def test08_game(self):
        sentence = 'SENTENCE'
        owner_id = 15

        # Create the game
        game_id = yield self.game.create(owner_id)

        game_info, players_id_list = yield self.game.game(None)
        self.assertEquals({'board': None,
                           'cards': None,
                           'id': game_id,
                           'ready': None,
                           'countdown_finish': None,
                           'owner': False,
                           'owner_id': owner_id,
                           'players': [{'id': owner_id,
                                        'vote': None,
                                        'win': u'n',
                                        'picked': None,
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None}],
                           'self': None,
                           'sentence': None,
                           'winner_card': None,
                           'state': u'create',
                           'invited': None,
                           'modified': self.game.modified}, game_info)
        self.assertEquals(players_id_list, [owner_id])

        # Set the card
        owner = yield self.game.player2game(owner_id)
        winner_card = owner['cards'][0]
        yield self.game.set_card(owner_id, winner_card)

        game_info, players_id_list = yield self.game.game(None)
        self.assertEquals({'board': None,
                           'cards': None,
                           'id': game_id,
                           'ready': None,
                           'countdown_finish': None,
                           'owner': False,
                           'owner_id': owner_id,
                           'players': [{'id': owner_id,
                                        'vote': None,
                                        'win': u'n',
                                        'picked': '',
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None}],
                           'self': None,
                           'sentence': None,
                           'winner_card': '',
                           'state': u'create',
                           'invited': None,
                           'modified': self.game.modified}, game_info)
        self.assertEquals(players_id_list, [owner_id])

        # Set the sentence/move to invitation state
        yield self.game.set_sentence(owner_id, sentence)
        player1 = 16
        card1 = 20
        player2 = 17
        card2 = 25
        player3 = 18
        player4 = 19
        invited = [player3, player4]
        for player_id in (player1, player2):
            result = yield self.game.participate(player_id)
            self.assertEquals([game_id], result['game_id'])
        yield self.game.invite(invited)

        # invitation state, visitor point of view
        self.game.modified = 444
        game_info, players_id_list = yield self.game.game(None)
        self.assertEquals({'board': None,
                           'cards': None,
                           'id': game_id,
                           'ready': False,
                           'countdown_finish': None,
                           'owner': False,
                           'owner_id': owner_id,
                           'players': [{'id': owner_id,
                                        'vote': None,
                                        'win': u'n',
                                        'picked': '',
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None},
                                       {'id': player1,
                                        'vote': None,
                                        'win': u'n',
                                        'picked': None,
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None},
                                       {'id': player2,
                                        'vote': None,
                                        'win': u'n',
                                        'picked': None,
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None}],
                           'self': None,
                           'sentence': u'SENTENCE',
                           'winner_card': '',
                           'state': u'invitation',
                           'invited': None,
                           'modified': self.game.modified}, game_info)
        self.assertEquals(players_id_list, [owner_id, player1, player2])

        # invitation state, owner point of view
        game_info, players_id_list = yield self.game.game(owner_id)
        self.assertEquals([winner_card], game_info['board'])
        self.assertTrue(winner_card in game_info['cards'])
        self.assertEquals(len(game_info['cards']), sum(map(lambda player: len(player['cards']), game_info['players'])))
        self.assertTrue(game_info['owner'])
        self.assertFalse(game_info['ready'])
        self.assertEquals(winner_card, game_info['winner_card'])
        self.assertEquals(game_id, game_info['id'])
        self.assertEquals(invited, game_info['invited'])
        self.assertNotEquals(id(invited), id(game_info['invited']))
        self.assertEquals(owner_id, game_info['owner_id'])
        self.assertEquals(owner_id, game_info['players'][0]['id'])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][0]['cards']))
        self.assertEquals(winner_card, game_info['players'][0]['picked'])
        self.assertEquals(player1, game_info['players'][1]['id'])
        self.assertEquals(None, game_info['players'][1]['picked'])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][1]['cards']))
        self.assertEquals(player2, game_info['players'][2]['id'])
        self.assertEquals(None, game_info['players'][2]['picked'])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][2]['cards']))
        self.assertEquals(winner_card, game_info['self'][0])
        self.assertEquals(None, game_info['self'][1])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['self'][2]))
        self.assertTrue(winner_card in game_info['self'][2])
        self.assertEquals(u'SENTENCE', game_info['sentence'])
        self.assertEquals(u'invitation', game_info['state'])
        self.assertEquals(players_id_list, [owner_id, player1, player2])

        # players vote
        result = yield self.game.pick(player1, card1)
        self.assertEquals([game_id], result['game_id'])
        result = yield self.game.pick(player2, card2)
        self.assertEquals([game_id], result['game_id'])

        # invitation state, owner point of view
        game_info, players_id_list = yield self.game.game(owner_id)
        self.assertTrue(game_info['ready'])
        # Assert modified is numeric; concrete type depends on architecture/implementation.
        self.assertTrue(isinstance(game_info['countdown_finish'], (int, long)))
        now_ms = time.time() * 1000
        self.assertTrue(game_info['countdown_finish'] > now_ms)
        self.assertEquals(players_id_list, [owner_id, player1, player2])

        # move to vote state
        result = yield self.game.voting(owner_id)
        self.assertEquals([game_id], result['game_id'])
        # vote state, owner point of view
        game_info, players_id_list = yield self.game.game(owner_id)
        game_info['board'].sort()
        board = [winner_card, card1, card2]
        board.sort()
        self.assertEquals(board, game_info['board'])
        self.assertTrue(winner_card in game_info['cards'])
        self.assertEquals(len(game_info['cards']), sum(map(lambda player: len(player['cards']), game_info['players'])))
        self.assertTrue(game_info['owner'])
        self.assertFalse(game_info['ready'])
        self.assertEquals(game_info['countdown_finish'], None)
        self.assertEquals(game_id, game_info['id'])
        self.assertEquals(owner_id, game_info['owner_id'])
        self.assertEquals(owner_id, game_info['players'][0]['id'])
        self.assertEquals(winner_card, game_info['players'][0]['picked'])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][0]['cards']))
        self.assertEquals(player1, game_info['players'][1]['id'])
        self.assertEquals(card1, game_info['players'][1]['picked'])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][1]['cards']))
        self.assertEquals(player2, game_info['players'][2]['id'])
        self.assertEquals(card2, game_info['players'][2]['picked'])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['players'][2]['cards']))
        self.assertEquals(winner_card, game_info['self'][0])
        self.assertEquals(None, game_info['self'][1])
        self.assertEquals(self.game.CARDS_PER_PLAYER, len(game_info['self'][2]))
        self.assertEquals(u'SENTENCE', game_info['sentence'])
        self.assertEquals(u'vote', game_info['state'])

        # every player vote
        result = yield self.game.vote(player1, card2)
        self.assertEquals([game_id], result['game_id'])
        result = yield self.game.vote(player2, card1)
        self.assertEquals([game_id], result['game_id'])
        # vote state, player point of view
        self.game.modified = 555
        game_info, players_id_list = yield self.game.game(player1)
        game_info['board'].sort()
        player1_cards = game_info['players'][1]['cards']
        countdown_finish = game_info['countdown_finish']
        self.assertTrue(isinstance(countdown_finish, (int, long)))
        now_ms = time.time() * 1000
        self.assertTrue(countdown_finish > now_ms)
        self.assertEquals({'board': board,
                           'cards': None,
                           'id': game_id,
                           'ready': True,
                           'countdown_finish': countdown_finish,
                           'owner': False,
                           'owner_id': owner_id,
                           'players': [{'id': owner_id,
                                        'vote': None,
                                        'win': u'n',
                                        'picked': '',
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None},
                                       {'id': player1,
                                        'vote': '',
                                        'win': u'n',
                                        'picked': card1,
                                        'cards': player1_cards,
                                        'score': 0,
                                        'level': 1,
                                        'score_next': 1,
                                        'score_left': 1,
                                        'score_prev': 0,
                                        'level_prev': 1,
                                        'earned_cards': None,
                                        'earned_cards_cur': None},
                                       {'id': player2,
                                        'vote': '',
                                        'win': u'n',
                                        'picked': '',
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None}],
                           'self': [card1, card2, player1_cards],
                           'sentence': u'SENTENCE',
                           'winner_card': '',
                           'state': u'vote',
                           'invited': None,
                           'modified': self.game.modified}, game_info)
        self.assertEquals(players_id_list, [owner_id, player1, player2])

    @defer.inlineCallbacks
    def test08_game_player_order(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, winner_card = yield self.create_game(owner_id, sentence)
        # move to invitation state
        player1 = 16
        card1 = 20
        player2 = 17
        card2 = 25
        player3 = 18
        player4 = 19
        invited = [player3, player4]
        for player_id in (player2, player1):
            result = yield self.game.participate(player_id)
            self.assertEquals([game_id], result['game_id'])
        yield self.game.invite(invited)

        # invitation state, visitor point of view
        self.game.modified = 444
        game_info, players_id_list = yield self.game.game(None)
        self.assertEquals({'board': None,
                           'cards': None,
                           'id': game_id,
                           'ready': False,
                           'countdown_finish': None,
                           'owner': False,
                           'owner_id': owner_id,
                           'players': [{'id': owner_id,
                                        'vote': None,
                                        'win': u'n',
                                        'picked': '',
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None},
                                       {'id': player2,
                                        'vote': None,
                                        'win': u'n',
                                        'picked': None,
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None},
                                       {'id': player1,
                                        'vote': None,
                                        'win': u'n',
                                        'picked': None,
                                        'cards': None,
                                        'score': None,
                                        'level': None,
                                        'score_next': None,
                                        'score_left': None,
                                        'score_prev': None,
                                        'level_prev': None,
                                        'earned_cards': None,
                                        'earned_cards_cur': None}],
                           'self': None,
                           'sentence': u'SENTENCE',
                           'winner_card': '',
                           'state': u'invitation',
                           'invited': None,
                           'modified': self.game.modified}, game_info)

    @defer.inlineCallbacks
    def test08_game_countdown_timeout(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, winner_card = yield self.create_game(owner_id, sentence)
        # move to invitation state
        player1 = 16
        card1 = 20
        player2 = 17
        card2 = 25
        for player_id in (player1, player2):
            result = yield self.game.participate(player_id)

        # change countdown duration prior to game ready
        yield self.game.set_countdown(1)

        # players vote
        result = yield self.game.pick(player1, card1)
        self.assertEquals([game_id], result['game_id'])
        result = yield self.game.pick(player2, card2)
        self.assertEquals([game_id], result['game_id'])

        game_info, players_id_list = yield self.game.game(owner_id)
        now_ms = time.time() * 1000
        self.assertTrue(now_ms < game_info['countdown_finish'] < now_ms + 1000)

        # move to vote state manually
        result = yield self.game.voting(owner_id)

        # every player vote
        result = yield self.game.vote(player1, card2)
        self.assertEquals([game_id], result['game_id'])
        result = yield self.game.vote(player2, card1)
        self.assertEquals([game_id], result['game_id'])

        # change countdown duration after game ready
        yield self.game.set_countdown(0.01)

        # auto move to complete state
        d = self.game.poll({'modified':[self.game.get_modified()]})
        def check(result):
            game_info = yield self.game.game(owner_id)
            self.assertEqual(game_info['state'], 'complete')
            self.assertEqual(game_info['countdown_finish'], None)
            self.assertEqual(result, None)
        d.addCallback(check)

    @defer.inlineCallbacks
    def test09_invitation(self):
        #
        # create a game and invite players
        #
        sentence = 'SENTENCE'
        owner_id = 15
        invited = [20, 21]
        game_id, winner_card = yield self.create_game(owner_id, sentence)
        self.assertEquals([owner_id], self.game.get_players())
        
        self.checked = False
        d = self.game.invite(invited)
        def check(result):
            self.checked = True
            self.assertNotEquals(id(invited), id(result['invited']))
            return result
        d.addCallback(check)
        result = yield d
        self.assertTrue(self.checked)
        self.assertEquals(result['type'], 'invite')
        self.assertEquals(result['invited'], invited)
        self.assertEquals([game_id], result['game_id'])
        self.assertEquals(invited, self.game.invited)
        self.assertEquals([owner_id] + invited, self.game.get_players())
        c = self.db.cursor()
        c.execute("SELECT * FROM invitations WHERE game_id = %d" % game_id)
        self.assertEquals(c.fetchall(), [(invited[0], game_id),
                                     (invited[1], game_id)])
        # inviting the same players twice is a noop
        result = yield self.game.invite(invited)
        self.assertEquals(result['type'], 'invite')
        self.assertEquals(result['invited'], [])
        #
        # load an existing game, invitations included
        #
        other_game = CardstoriesGame(self.service, self.game.get_id())
        other_game.load(c)
        self.assertEquals(other_game.get_players(), [owner_id] + invited)
        other_game.destroy()
        participation = yield self.game.participate(invited[0])
        self.assertEquals([game_id], result['game_id'])
        c.execute("SELECT * FROM invitations WHERE game_id = %d" % game_id)
        self.assertEquals(c.fetchall(), [(invited[1], game_id)])
        yield self.game.voting(owner_id)
        c.execute("SELECT * FROM invitations WHERE game_id = %d" % game_id)
        self.assertEquals(c.fetchall(), [])
        c.close()

    @defer.inlineCallbacks
    def test10_touch(self):
        owner_id = 15
        game_id = yield self.game.create(owner_id)
        result = yield self.game.touch()
        self.assertEquals([game_id], result['game_id'])
        self.assertEquals(self.game.modified, result['modified'][0])
        
    @defer.inlineCallbacks
    def test11_leave(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, card = yield self.create_game(owner_id, sentence)
        cards = [card]
        players = [ 16, 17 ]
        for player_id in players:
            yield self.game.participate(player_id)
            player = yield self.game.player2game(player_id)
        modified = self.game.get_modified()
        self.assertTrue(players[0] in self.game.get_players())
        self.assertTrue(players[1] in self.game.get_players())
        result = yield self.game.leave_api({'player_id': players,
                                            'game_id': [self.game.get_id()] })
        self.assertTrue(self.game.get_modified() > modified)
        self.assertEqual(result['deleted'], 2)
        self.assertFalse(players[0] in self.game.get_players())
        self.assertFalse(players[1] in self.game.get_players())

    @defer.inlineCallbacks
    def test12_cancel(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, card = yield self.create_game(owner_id, sentence)
        cards = [card]
        players = [ 16, 17 ]
        for player_id in players:
            yield self.game.participate(player_id)
        invited = 20
        yield self.game.invite([invited])
        self.assertEquals([owner_id] + players + [invited], self.game.get_players())

        game_info, players_game_info = yield self.game.game(owner_id)
        self.assertEquals(game_info['state'], u'invitation')
        self.assertEquals([ player['id'] for player in game_info['players']], [owner_id] + players)
        d = self.game.poll({'modified':[self.game.get_modified()]})
        def check(result):
            self.assertEqual(result['type'], 'cancel')
            self.assertEqual(result['modified'], [self.game.modified])
            self.game.canceled = True
        d.addCallback(check)
        result = yield self.game.cancel()
        self.assertTrue(self.game.canceled)
        self.assertEquals(result, {})
        self.game.service = self.service
        game_info, players_game_info = yield self.game.game(owner_id)
        self.assertEquals(game_info['state'], u'canceled')
        self.assertEquals([ player['id'] for player in game_info['players']], [owner_id] + players)

    @defer.inlineCallbacks
    def test13_state_change(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, winner_card = yield self.create_game(owner_id, sentence)
        players = [ 16, 17 ]
        for player_id in players:
            yield self.game.participate(player_id)
            player = yield self.game.player2game(player_id)
            card = player['cards'][0]
            yield self.game.pick(player_id, card)

        result = yield self.game.state_change()
        self.assertEquals(result, CardstoriesGame.STATE_CHANGE_TO_VOTE)

        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % game_id)
        board = c.fetchone()[0]
        winner_id = 16
        yield self.game.vote(winner_id, winner_card)
        loser_id = 17
        yield self.game.vote(loser_id, 120)
        result = yield self.game.state_change()
        self.assertEquals(result, CardstoriesGame.STATE_CHANGE_TO_COMPLETE)
        c.execute("SELECT win FROM player2game WHERE game_id = %d AND player_id != %d" % (game_id, owner_id))
        self.assertEqual(u'y', c.fetchone()[0])
        self.assertEqual(u'n', c.fetchone()[0])
        self.assertEqual(c.fetchone(), None)
        c.close()

    @defer.inlineCallbacks
    def test14_state_change_cancel_create(self):
        owner_id = 15
        game_id = yield self.game.create(owner_id)
        result = yield self.game.state_change()
        self.assertEquals(result, CardstoriesGame.STATE_CHANGE_CANCEL)

    @defer.inlineCallbacks
    def test14_state_change_cancel_invitation(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, winner_card = yield self.create_game(owner_id, sentence)
        cards = [winner_card]
        pick_players = [ 16 ]
        players = pick_players + [ 18 ]
        for player_id in players:
            yield self.game.participate(player_id)
        for player_id in pick_players:
            player = yield self.game.player2game(player_id)
            card = player['cards'][0]
            cards.append(card)
            yield self.game.pick(player_id, card)
        result = yield self.game.state_change()
        self.assertEquals(result, CardstoriesGame.STATE_CHANGE_CANCEL)

    @defer.inlineCallbacks
    def test15_state_change_cancel_voting(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, winner_card = yield self.create_game(owner_id, sentence)
        voting_players = [ 16 ]
        players = voting_players + [ 17, 18 ]
        for player_id in players:
            yield self.game.participate(player_id)
            player = yield self.game.player2game(player_id)
            card = player['cards'][0]
            yield self.game.pick(player_id, card)
        
        yield self.game.voting(owner_id)

        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % game_id)
        board = c.fetchone()[0]
        winner_id = 16
        yield self.game.vote(winner_id, winner_card)
        self.assertEquals(self.game.get_players(), [owner_id] + players)
        result = yield self.game.state_change()
        self.assertEquals(result, CardstoriesGame.STATE_CHANGE_CANCEL)

    @defer.inlineCallbacks
    def test16_timeout(self):
        sentence = 'SENTENCE'
        owner_id = 15
        self.game.settings['game-timeout'] = 0.5
        game_id, winner_card = yield self.create_game(owner_id, sentence)
        d = self.game.poll({'modified': [self.game.get_modified()]})
        def check(result):
            self.assertEqual(self.game.get_players(), [owner_id])
            self.assertEqual(result['type'], 'cancel')
            self.assertEqual(result['modified'], [self.game.modified])
            self.game.timedout = True
            return result
        d.addCallback(check)
        result = yield d
        self.assertTrue(self.game.timedout)

    @defer.inlineCallbacks
    def test17_nonexistent_game(self):
        raises_CardstoriesException = False
        error_code = None
        try:
            self.game.id = 12332123
            yield self.game.game(None)
        except CardstoriesWarning as e:
            raises_CardstoriesException = True
            error_code = e.code
        self.assertTrue(raises_CardstoriesException)
        self.assertEqual('GAME_DOES_NOT_EXIST', error_code)

    @defer.inlineCallbacks
    def test18_complete_and_game_race(self):
        sentence = 'SENTENCE'
        owner_id = 15
        game_id, winner_card = yield self.create_game(owner_id, sentence)
        voting_players = [ 16, 17 ]
        players = voting_players + [ 18 ]
        for player_id in players:
            yield self.game.participate(player_id)
            player = yield self.game.player2game(player_id)
            card = player['cards'][0]
            yield self.game.pick(player_id, card)
        
        yield self.game.voting(owner_id)

        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % game_id)
        board = c.fetchone()[0]
        winner_id = 16
        yield self.game.vote(winner_id, winner_card)
        loser_id = 17
        yield self.game.vote(loser_id, 120)
        self.assertEquals(self.game.get_players(), [owner_id] + players)
        #
        # the game is about to be completed.
        # Create the race condition by:
        # a) calling game() and block it on the first runQuery
        # b) calling complete() and unblock the game() when it returns
        # c) resume game() which then needs to cope with the fact 
        #    that it is now using a game that has been destroyed
        #
        #
        # Replace the runQuery function by a wrapper that blocks the query.
        # It does it by creating a deferred that will run the original 
        # query when it fires. This deferred will need to be fired manually
        # by the enclosing test, when it needs it. This effectively creates
        # a condition that simulates a lag because the database is not
        # available.
        #
        original_runQuery = self.game.service.db.runQuery
        query_deferred = defer.Deferred()
        def fake_runQuery(*args):
            def f(result):
                r = original_runQuery(*args)
                return r
            query_deferred.addCallback(f)
            #
            # Now that the query has been wrapped in the deferred and the
            # calling function has been interrupted, restore the original
            # runQuery function so that the code keeps running as expected.
            #
            self.game.service.db.runQuery = original_runQuery
            return query_deferred
        # 
        # Because the runQuery is a fake, the deferred returned by self.game.game()
        # will actually be the deferred returned by the fake_runQuery function.
        # As a consequence the game.game() function will be blocked in the middle
        # of its execution, waiting for the deferred returned by fake_runQuery to 
        # be fired.
        #
        self.game.service.db.runQuery = fake_runQuery
        game_deferred = self.game.game(owner_id)
        #
        # The complete() function returns a deferred. The triggerGame() function is
        # added to the callback list of this deferred so that it resumes the interrupted
        # game.game() call by firing the deferred returned by fake_runQuery.
        # As a consequence, game.game() will complete its execution after the game has
        # been destroyed. It must cope with this because such concurrency will happen,
        # even if only rarely.
        #
        complete_deferred = self.game.complete(owner_id)
        def triggerGame(result):
            #
            # call destroy to reproduce the conditions of the service.py
            # complete() function. 
            #
            self.game.destroy()
            query_deferred.callback(True)
            return result
        complete_deferred.addCallback(triggerGame)
        result = yield complete_deferred
        game_result = yield game_deferred
        self.assertEquals(result['type'], 'complete')
        c.close()

    @defer.inlineCallbacks
    def test19_countdown(self):
        sentence = 'SENTENCE'
        owner_id = 15
        yield self.game.create(owner_id)
        owner = yield self.game.player2game(owner_id)
        winner_card = owner['cards'][0]
        self.assertEqual(self.game.get_countdown_duration(), self.game.DEFAULT_COUNTDOWN_DURATION)
        self.assertFalse(self.game.is_countdown_active())
        self.assertEqual(self.game.get_countdown_finish(), None)

        yield self.game.set_card(owner_id, winner_card)
        self.assertEqual(self.game.get_countdown_duration(), self.game.DEFAULT_COUNTDOWN_DURATION)
        self.assertFalse(self.game.is_countdown_active())
        self.assertEqual(self.game.get_countdown_finish(), None)

        yield self.game.set_sentence(owner_id, sentence)
        self.assertEqual(self.game.get_countdown_duration(), self.game.DEFAULT_COUNTDOWN_DURATION)
        self.assertFalse(self.game.is_countdown_active())
        self.assertEqual(self.game.get_countdown_finish(), None)

        duration = 200
        self.game.set_countdown_duration(duration)
        self.assertEqual(self.game.get_countdown_duration(), duration)
        self.assertFalse(self.game.is_countdown_active())
        self.assertEqual(self.game.get_countdown_finish(), None)

        self.game.start_countdown()
        self.assertTrue(self.game.is_countdown_active())
        self.assertTrue(isinstance(self.game.get_countdown_finish(), (int, long)))
        now_ms = time.time() * 1000
        self.assertTrue(self.game.get_countdown_finish() > now_ms)

        self.game.clear_countdown()
        self.assertEqual(self.game.get_countdown_duration(), self.game.DEFAULT_COUNTDOWN_DURATION)
        self.assertFalse(self.game.is_countdown_active())
        self.assertEqual(self.game.get_countdown_finish(), None)

        self.game.set_countdown_duration(0.01)
        self.game.start_countdown()
        d = self.game.poll({'modified': [self.game.get_modified()]})
        def check(result):
            self.assertFalse(self.game.is_countdown_active())
            self.assertEqual(result, None)
        d.addCallback(check)

    @defer.inlineCallbacks
    def test20_pick_only_in_invitation_state(self):
        sentence = 'SENTENCE'
        owner_id = 19
        player1_id = 53
        player2_id = 54
        player3_id = 55
        game_id, winner_card = yield self.create_game(owner_id, sentence)

        # Three players joining the game.
        for player_id in (player1_id, player2_id, player3_id):
            yield self.game.participate(player_id)

        # Two players pick cards.
        # They can do that while the game is in the 'invitation' state.
        yield self.game.pick(player1_id, 1)
        yield self.game.pick(player2_id, 2)

        # Move the game to the 'vote' state.
        yield self.game.voting(owner_id)

        # The third player can't pick a card anymore.
        raises_CardstoriesException = False
        error_code = None
        error_data = {}
        try:
            yield self.game.pick(player3_id, 3)
        except CardstoriesWarning as e:
            raises_CardstoriesException = True
            error_code = e.code
            error_data = e.data
        self.assertTrue(raises_CardstoriesException)
        self.assertEqual('WRONG_STATE_FOR_PICKING', error_code)
        self.assertEqual('vote', error_data['state'])

    @defer.inlineCallbacks
    def test21_vote_only_in_vote_state(self):
        sentence = 'SENTENCE'
        owner_id = 12
        player1_id = 13
        player2_id = 14
        player3_id = 15
        game_id, winner_card = yield self.create_game(owner_id, sentence)

        # Three players joining the game.
        for player_id in (player1_id, player2_id, player3_id):
            yield self.game.participate(player_id)

        # The players pick cards.
        yield self.game.pick(player1_id, 1)
        yield self.game.pick(player2_id, 2)
        yield self.game.pick(player3_id, 3)

        # Try to vote now (not in the 'vote' state yet!).
        raises_CardstoriesException = False
        error_code = None
        error_data = {}
        try:
            yield self.game.vote(player1_id, 25)
        except CardstoriesWarning as e:
            raises_CardstoriesException = True
            error_code = e.code
            error_data = e.data
        self.assertTrue(raises_CardstoriesException)
        self.assertEqual('WRONG_STATE_FOR_VOTING', error_code)
        self.assertEqual('invitation', error_data['state'])

        # Move the game to the 'vote' state.
        yield self.game.voting(owner_id)

        # Two players vote.
        yield self.game.vote(player1_id, 25)
        yield self.game.vote(player2_id, 24)

        # Save reference to the db since the complete method will delete the
        # service object from the game.
        db = self.game.service.db

        # Move the game to the complete state and simulate a race condition
        # where the third player votes after the results have already been
        # calculated.
        yield self.game.complete(owner_id)

        # The third player can't vote anymore.
        # The exception here isn't the CardstoriesWarning, because the code
        # fails prior to that (since the game has been destroyed),
        # and the user error response is generated by the service, not the game.
        # So the only important thing to assert here is that trying to vote fails.
        raises_exception = False
        try:
            yield self.game.vote(player3_id, 25)
        except:
            raises_exception = True
        self.assertTrue(raises_exception)

        vote = yield db.runQuery("SELECT vote FROM player2game WHERE game_id = ? AND player_id = ?", [ self.game.get_id(), player3_id ])
        self.assertEquals(None, vote[0][0])

    @defer.inlineCallbacks
    def test22_game_is_destroy_upon_complete(self):
        sentence = 'SENTENCE'
        owner_id = 12
        player1_id = 13
        player2_id = 14
        game_id, winner_card = yield self.create_game(owner_id, sentence)

        # The players join the game.
        yield self.game.participate(player1_id)
        yield self.game.participate(player2_id)
        # The players pick cards.
        yield self.game.pick(player1_id, 1)
        yield self.game.pick(player2_id, 2)
        # Move the game to the 'vote' state.
        yield self.game.voting(owner_id)
        # The players vote.
        yield self.game.vote(player1_id, 25)
        yield self.game.vote(player2_id, 24)

        # Mock out the game.destroy() method.
        orig_destroy = CardstoriesGame.destroy
        def fake_destroy(self):
            self.destroy_called = True
            orig_destroy(self)
        CardstoriesGame.destroy = fake_destroy

        # Complete the game, which should in turn call game.destroy().
        yield self.game.complete(owner_id)
        CardstoriesGame.destroy = orig_destroy
        self.assertTrue(self.game.destroy_called)
        # Clean up the mock.

    @defer.inlineCallbacks
    def test23_game_before_player_is_created(self):
        sentence = 'SENTENCE'
        owner_id = 12
        player1_id = 13
        player2_id = 14

        # Mock out the game.playerInteraction() method.
        orig_playerInteraction = CardstoriesGame.playerInteraction
        def fake_playerInteraction(self, transaction, player_id):
            pass
        CardstoriesGame.playerInteraction = fake_playerInteraction

        game_id, winner_card = yield self.create_game(owner_id, sentence)
        yield self.game.participate(player1_id)
        yield self.game.participate(player2_id)
        yield self.game.pick(player1_id, 1)
        yield self.game.pick(player2_id, 2)
        yield self.game.voting(owner_id)
        yield self.game.vote(player1_id, 25)
        yield self.game.vote(player2_id, 24)
        yield self.game.complete(owner_id)

        # Clean up the mock.
        CardstoriesGame.playerInteraction = orig_playerInteraction


def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test18_"
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
