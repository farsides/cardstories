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

# Imports ##################################################################

import sys, os
sys.path.insert(0, os.path.abspath("..")) # so that for M-x pdb works
import sqlite3
from datetime import datetime, timedelta

from twisted.trial import unittest, runner, reporter
from cardstories.service import CardstoriesService
import cardstories.event_log as event_log
from mailing import aggregate


# Classes ##################################################################

class AggregateTest(unittest.TestCase):

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
        return self.service.stopService()

    def test01_get_player_game_ids(self):
        c = self.db.cursor()
        player_id = 1231
        game_ids = [34, 64, 322, 340]
        # fill in some game_ids for player.
        for game_id in game_ids:
            c.execute('insert into player2game (player_id, game_id) values (?, ?)', [player_id, game_id])
        # fill in some bogus ones.
        c.execute('insert into player2game (player_id, game_id) values (?, ?)', [player_id + 3, game_ids[0]])
        c.execute('insert into player2game (player_id, game_id) values (?, ?)', [player_id + 2, game_ids[0]])
        c.execute('insert into player2game (player_id, game_id) values (?, ?)', [player_id + 2, game_ids[0] + 12])

        result = aggregate.get_player_game_ids(c, player_id)
        self.assertEquals(sorted(result), sorted(game_ids))

    def test02_get_game_activities(self):
        c = self.db.cursor()
        game1 = 99
        game2 = 199
        sentence1 = 'This Story'
        sentence2 = 'That Story'
        player1 = 11
        player2 = 12
        invitee = 878

        # Define some datetimes.
        now = datetime.now()
        an_hour_ago = now - timedelta(hours=1)
        six_hours_ago = now - timedelta(hours=6)
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)
        three_days_ago = now - timedelta(days=3)

        # Create two games.
        sql = 'INSERT INTO games (id, owner_id, state, sentence, created) VALUES (?, ?, ?, ?, ?)'
        c.execute(sql, [game1, player1, 'voting', sentence1, two_days_ago])
        c.execute(sql, [game2, player1, 'invitation', sentence2, yesterday])

        # Fill in some log data.
        data = [
            # Game 1
            [game1, two_days_ago, event_log.GAME_CREATED, player1, ''],
            [game1, two_days_ago + timedelta(seconds=1), event_log.OWNER_CHOSE_CARD, player1, 22],
            [game1, two_days_ago + timedelta(seconds=2), event_log.OWNER_WROTE_STORY, player1, sentence1],
            [game1, six_hours_ago, event_log.PLAYER_JOINED, player2, 33],
            [game1, now, event_log.PLAYER_VOTED, player2, 33],
            # Game 2
            [game2, yesterday, event_log.GAME_CREATED, player1, ''],
            [game2, yesterday + timedelta(seconds=1), event_log.OWNER_CHOSE_CARD, player1, 34],
            [game2, six_hours_ago, event_log.OWNER_WROTE_STORY, player1, sentence2],
            [game2, an_hour_ago, event_log.PLAYER_INVITED, player1, invitee],
            [game2, an_hour_ago + timedelta(seconds=1), event_log.PLAYER_JOINED, invitee, ''],
            [game2, now, event_log.PLAYER_PICKED_CARD, invitee, 23]
        ]
        for d in data:
            c.execute('INSERT INTO event_logs (game_id, timestamp, event_type, player_id, data) VALUES (?, ?, ?, ?, ?)', d)
        player_id = 1231

        result = aggregate.get_game_activities(c, [game1], player1, happened_since=three_days_ago)
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]['game_id'], game1)
        self.assertEquals(result[0]['state'], 'voting')
        self.assertEquals(result[0]['owner_name'], 'You')
        events = result[0]['events']
        self.assertEquals(len(events), 5)
        self.assertEquals(events[0], 'You created the game')
        self.assertEquals(events[1], 'You chose the card')
        self.assertEquals(events[2], 'You wrote the story')
        self.assertEquals(events[3], 'John Johnson joined the game')
        self.assertEquals(events[4], 'John Johnson voted')

        since = six_hours_ago - timedelta(seconds=1)
        result = aggregate.get_game_activities(c, [game1, game2], invitee, happened_since=since)
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0]['game_id'], game1)
        self.assertEquals(result[0]['state'], 'voting')
        self.assertEquals(result[0]['owner_name'], 'John Johnson')
        events1 = result[0]['events']
        self.assertEquals(len(events1), 2)
        self.assertEquals(events1[0], 'John Johnson joined the game')
        self.assertEquals(events1[1], 'John Johnson voted')
        events2 = result[1]['events']
        self.assertEquals(len(events2), 4)
        self.assertEquals(events2[0], 'John Johnson wrote the story')
        self.assertEquals(events2[1], 'John Johnson invited You to join the game')
        self.assertEquals(events2[2], 'You joined the game')
        self.assertEquals(events2[3], 'You picked a fake card')

    def test03_get_available_games(self):
        c = self.db.cursor()
        owner_id = 42

        # Define some datetimes.
        now = datetime.now()
        an_hour_ago = now - timedelta(hours=1)
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)
        three_days_ago = now - timedelta(days=3)

        # Create some games.
        sql = 'INSERT INTO games (id, owner_id, state, sentence, created) VALUES (?, ?, ?, ?, ?)'
        games = [
            [1, 'invitation', 'Story 1', three_days_ago],
            [2, 'invitation', 'Story 2', two_days_ago],
            [3, 'create', '', yesterday],
            [4, 'voting', 'Story 4', yesterday],
            [5, 'canceled', 'Story 5', an_hour_ago],
            [6, 'complete', 'Story 6', an_hour_ago],
            [7, 'invitation', 'Story 7', now],
        ]
        for game in games:
            c.execute(sql, [game[0], owner_id, game[1], game[2], game[3]])

        # Fetching all available games since two days ago should yeild two results.
        result = aggregate.get_available_games(c, two_days_ago)
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0]['game_id'], 2)
        self.assertEquals(result[0]['owner_name'], 'John Johnson')
        self.assertEquals(result[0]['sentence'], 'Story 2')
        self.assertEquals(result[1]['game_id'], 7)
        self.assertEquals(result[1]['owner_name'], 'John Johnson')
        self.assertEquals(result[1]['sentence'], 'Story 7')

        # Fetching all available games since three days ago should yeild three results,
        # but we are excluding three of them with the third optional parameter,
        # so there should be only one game in the result.
        result = aggregate.get_available_games(c, three_days_ago, [2, 7, 888])
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]['game_id'], 1)
        self.assertEquals(result[0]['owner_name'], 'John Johnson')
        self.assertEquals(result[0]['sentence'], 'Story 1')


    def test03_get_completed_games(self):
        c = self.db.cursor()
        owner_id = 42

        # Define some datetimes.
        now = datetime.now()
        an_hour_ago = now - timedelta(hours=1)
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)
        three_days_ago = now - timedelta(days=3)

        # Create some games.
        sql = 'INSERT INTO games (id, owner_id, state, sentence, created) VALUES (?, ?, ?, ?, ?)'
        games = [
            [1, 'invitation', 'Story 1', three_days_ago],
            [2, 'create', '', two_days_ago],
            [3, 'complete', 'Story 3', yesterday],
            [4, 'voting', 'Story 4', yesterday],
            [5, 'canceled', 'Story 5', an_hour_ago],
            [6, 'complete', 'Story 6', an_hour_ago],
            [7, 'invitation', 'Story 7', now],
        ]
        for game in games:
            c.execute(sql, [game[0], owner_id, game[1], game[2], game[3]])

        # Fetching completed games since two days ago should yeild two results.
        result = aggregate.get_completed_games(c, two_days_ago)
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0]['game_id'], 3)
        self.assertEquals(result[0]['owner_name'], 'John Johnson')
        self.assertEquals(result[0]['sentence'], 'Story 3')
        self.assertEquals(result[1]['game_id'], 6)
        self.assertEquals(result[1]['owner_name'], 'John Johnson')
        self.assertEquals(result[1]['sentence'], 'Story 6')

        # Fetching completed games since three days ago should again yeild two results,
        # but we are excluding one of them with the third optional parameter,
        # so there should be only one game in the result.
        result = aggregate.get_available_games(c, three_days_ago, [1, 4, 888])
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0]['game_id'], 7)
        self.assertEquals(result[0]['owner_name'], 'John Johnson')
        self.assertEquals(result[0]['sentence'], 'Story 7')


# Main #####################################################################

def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(AggregateTest))

    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

