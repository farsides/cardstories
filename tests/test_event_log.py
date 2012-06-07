# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Farsides <contact@farsides.com>
#
# Authors:
#          Matjaz Gregoric <mtyaka@gmail.com>
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

from twisted.internet import defer
from twisted.trial import unittest, runner, reporter

import cardstories.event_log as event_log
from cardstories.service import CardstoriesService
from cardstories.game import CardstoriesGame


class CardstoriesEventLogTest(unittest.TestCase):

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

    # Since the logging is all async, the tests would be a nightmare without
    # enforcing events to be logged serially as they happen.
    # In order to do this, we wait by poking at the DB in a loop until the
    # expected number of records exists in the DB.
    def wait_for_logs(self, game_id, expected_nr):
        c = self.db.cursor()
        while True:
            time.sleep(0.005)
            c.execute('SELECT COUNT(*) FROM event_logs WHERE game_id = ?', [game_id])
            if c.fetchone()[0] == expected_nr:
                break

    @defer.inlineCallbacks
    def test01_log_game_events(self):
        owner_id = 42
        player1_id = 84
        player2_id = 86
        sentence = 'The Sentence.'

        # 1 - Should log creation.
        game_id = yield self.game.create(owner_id)
        self.wait_for_logs(game_id, 1)

        # 2 - Should log card set.
        owner = yield self.game.player2game(owner_id)
        winner_card = owner['cards'][0]
        yield self.game.set_card(owner_id, winner_card)
        self.wait_for_logs(game_id, 2)

        # 3 -Should log sentence set.
        yield self.game.set_sentence(owner_id, sentence)
        self.wait_for_logs(game_id, 3)

        # 4 - Should log invitation (player1 only).
        yield self.game.invite([player1_id])
        self.wait_for_logs(game_id, 4)

        # 5 & 6 - Should log joining (both players).
        yield self.game.participate(player1_id)
        self.wait_for_logs(game_id, 5)
        yield self.game.participate(player2_id)
        self.wait_for_logs(game_id, 6)

        # 7 & 8 - Should log players picking cards.
        player1 = yield self.game.player2game(player1_id)
        picked_card1 = player1['cards'][0]
        yield self.game.pick(player1_id, picked_card1)
        self.wait_for_logs(game_id, 7)
        player2 = yield self.game.player2game(player2_id)
        picked_card2 = player1['cards'][0]
        yield self.game.pick(player2_id, picked_card2)
        self.wait_for_logs(game_id, 8)

        # 9 - Should log game moved into voting.
        yield self.game.voting(owner_id)
        self.wait_for_logs(game_id, 9)

        # 10 & 11 - Should log players voting for cards.
        yield self.game.vote(player1_id, winner_card)
        self.wait_for_logs(game_id, 10)
        yield self.game.vote(player2_id, picked_card1)
        self.wait_for_logs(game_id, 11)

        # 12 - Should log game completed.
        yield self.game.complete(owner_id)
        self.wait_for_logs(game_id, 12)

        # Now lets check the logs table.
        c = self.db.cursor()
        # Wait until the logs are written (they're written asynchronously)
        c.execute('SELECT event_type, player_id, data FROM event_logs WHERE game_id = ? ORDER BY timestamp', [game_id])
        # Twelve events should be logged.
        rows = c.fetchall()
        self.assertEqual((event_log.GAME_CREATED, owner_id, None), rows[0])
        self.assertEqual((event_log.OWNER_CHOSE_CARD, owner_id, str(winner_card)), rows[1])
        self.assertEqual((event_log.OWNER_WROTE_STORY, owner_id, sentence), rows[2])
        self.assertEqual((event_log.PLAYER_INVITED, owner_id, str(player1_id)), rows[3])
        self.assertEqual((event_log.PLAYER_JOINED, player1_id, None), rows[4])
        self.assertEqual((event_log.PLAYER_JOINED, player2_id, None), rows[5])
        self.assertEqual((event_log.PLAYER_PICKED_CARD, player1_id, str(picked_card1)), rows[6])
        self.assertEqual((event_log.PLAYER_PICKED_CARD, player2_id, str(picked_card2)), rows[7])
        self.assertEqual((event_log.GAME_MOVED_TO_VOTING, owner_id, None), rows[8])
        self.assertEqual((event_log.PLAYER_VOTED, player1_id, str(winner_card)), rows[9])
        self.assertEqual((event_log.PLAYER_VOTED, player2_id, str(picked_card1)), rows[10])
        self.assertEqual((event_log.GAME_COMPLETED, owner_id, None), rows[11])

        c.close()

    @defer.inlineCallbacks
    def test01_log_canceled_game_events(self):
        owner_id = 4
        player_id = 8
        sentence = 'Some Sentence.'

        # 1 - Should log creation.
        game_id = yield self.game.create(owner_id)
        self.wait_for_logs( game_id, 1)

        # 2 - Should log card set.
        owner = yield self.game.player2game(owner_id)
        winner_card = owner['cards'][0]
        yield self.game.set_card(owner_id, winner_card)
        self.wait_for_logs( game_id, 2)

        # 3 -Should log sentence set.
        yield self.game.set_sentence(owner_id, sentence)
        self.wait_for_logs( game_id, 3)

        # 4 - Should log joining.
        yield self.game.participate(player_id)
        self.wait_for_logs( game_id, 4)

        # 5 - Should log player leaving.
        yield self.game.leave([player_id])
        self.wait_for_logs( game_id, 5)

        # 6 - Should log game cancelation.
        yield self.game.cancel()
        self.wait_for_logs(game_id, 6)

        # Now lets check the logs table.
        c = self.db.cursor()
        c.execute('SELECT event_type, player_id, data FROM event_logs WHERE game_id = ? ORDER BY timestamp', [game_id])
        # Twelve events should be logged.
        rows = c.fetchall()
        self.assertEqual((event_log.GAME_CREATED, owner_id, None), rows[0])
        self.assertEqual((event_log.OWNER_CHOSE_CARD, owner_id, str(winner_card)), rows[1])
        self.assertEqual((event_log.OWNER_WROTE_STORY, owner_id, sentence), rows[2])
        self.assertEqual((event_log.PLAYER_JOINED, player_id, None), rows[3])
        self.assertEqual((event_log.PLAYER_LEFT, player_id, None), rows[4])
        self.assertEqual((event_log.GAME_CANCELED, owner_id, None), rows[5])

        c.close()

# Main ########################################################################

def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesEventLogTest))
    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

