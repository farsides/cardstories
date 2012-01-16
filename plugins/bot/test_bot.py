# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Authors:
#          Xavier Antoviaque <xavier@antoviaque.org>
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

# Imports ##################################################################

import sys, os
from mock import Mock

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer

from cardstories.service import CardstoriesService
from plugins.bot import bot


# Classes ##################################################################

class BotTest(unittest.TestCase):

    # initialise our test with a service that we can use during testing and a testing database
    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)

        self.service = CardstoriesService({'db': self.database,
                                           'plugins-confdir': '../fixture',
                                           'plugins-libdir': 'LIBDIR',
                                           'static': 'STATIC'
                                           })
        self.service.auth = Mock()
        self.service.startService()

    def tearDown(self):
        # kill the service we started before the test
        return self.service.stopService()

    @defer.inlineCallbacks
    def game_create(self):
        self.winner_card = winner_card = 5
        sentence = 'SENTENCE'
        self.owner_id = 15
        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [self.owner_id]})

        defer.returnValue(game)

    @defer.inlineCallbacks
    def game_to_vote(self, game_id):
        yield self.service.voting({ 'action': ['voting'],
                                    'game_id': [game_id],
                                    'owner_id': [self.owner_id] })
        self.assertTrue(self.service.games.has_key(game_id))
        defer.returnValue(True)

    @defer.inlineCallbacks
    def game_to_complete(self, game_id):
        yield self.service.complete({ 'action': ['complete'],
                                      'game_id': [game_id],
                                      'owner_id': [self.owner_id] })
        self.assertFalse(self.service.games.has_key(game_id))
        defer.returnValue(True)

    @defer.inlineCallbacks
    def test01_play_game(self):
        mock_reactor = bot.reactor = Mock() # Don't delay calls

        bot_plugin = bot.Plugin(self.service, [])
        self.assertEquals(bot_plugin.name(), 'bot')
        bots = [bot_plugin.bots[0], bot_plugin.bots[1], bot_plugin.bots[2]]
        self.assertEqual(bots[0].player_id, 2)
        self.assertEqual(bots[1].player_id, 3)
        self.assertEqual(bots[2].player_id, 4)

        # New game
        game = yield self.game_create()
        game_id = game['game_id']
        mock_reactor.callLater.assert_called_once_with(1, bot_plugin.check_need_player, game_id)
        mock_reactor.reset_mock()

        # Only the author in the game
        game, players_ids = yield bots[0].get_game_by_id(game_id)
        self.assertEqual(len(game['players']), 1)

        # Bots join
        for i in xrange(2):
            yield bot_plugin.check_need_player(game_id)
            self.assertEqual(mock_reactor.callLater.call_args_list,
                             [((2, bots[i].pick, game_id), {}),
                              ((1, bot_plugin.check_need_player, game_id), {})])
            mock_reactor.reset_mock()

            game, player_ids = yield bots[i].get_game_by_id(game_id)
            self.assertEqual(game['players'][i + 1]['id'], bots[i].player_id)
            self.assertEqual(game['players'][i + 1]['picked'], None)

        # Bots pick a card
        for i in xrange(2):
            yield bots[i].pick(game_id)
            self.assertFalse(mock_reactor.called)

            game, player_ids = yield bots[i].get_game_by_id(game_id)
            self.assertIsInstance(game['players'][i + 1]['picked'], int)
            self.assertEqual(game['players'][i + 1]['vote'], None)

        # Go to vote phase
        yield self.game_to_vote(game_id)
        self.assertEqual(mock_reactor.callLater.call_args_list,
                         [((3, bots[0].vote, game_id), {}),
                          ((3, bots[1].vote, game_id), {})])
        mock_reactor.reset_mock()

        # A bot should never join or pick at this stage
        joined = yield bots[2].join(game_id)
        self.assertFalse(joined)
        picked = yield bots[2].pick(game_id)
        self.assertFalse(picked)

        # Bots vote
        for i in xrange(2):
            yield bots[i].vote(game_id)
            self.assertFalse(mock_reactor.called)

            game, player_ids = yield bots[i].get_game_by_id(game_id)
            self.assertIsInstance(game['players'][i + 1]['picked'], int)
            self.assertEqual(game['players'][i + 1]['vote'], '')

        # A bot should never vote at this stage
        joined = yield bots[2].vote(game_id)
        self.assertFalse(joined)

    def test02_brain_not_implemented(self):
        brain = bot.Brain(None)
        self.assertRaises(NotImplementedError, brain.get_all_cards_scores_for_sentence, "Test")

    def test03_brain_weighted_card_choice(self):
        brain = bot.Brain(None)
        ranked_cards = [(1, 1), (2, 10000), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0)]
        chosen_card = brain.weighted_card_choice(ranked_cards)
        self.assertTrue(chosen_card == 1 or chosen_card == 2)

    @defer.inlineCallbacks
    def test04_nlwordmatcherbrain(self):
        bot_plugin = bot.Plugin(self.service, [])
        brain = bot.NLWordMatcherBrain(bot_plugin)

        ranked_cards = yield brain.sort_cards_by_ranking_for_sentence("word", [1, 2, 3])
        self.assertEquals(ranked_cards, [(3, 3), (2, 2), (1, 1)])


# Main #####################################################################

def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(BotTest))

    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

