# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Farsides <contact@farsides.com>
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

# Imports ####################################################################

import sys, os
sys.path.insert(0, os.path.abspath("../..")) # so that for M-x pdb works
from mock import Mock

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer

from cardstories.service import CardstoriesService
from plugins.table import table


# Classes ####################################################################

class Request:
    """
    Fake a request object holding the arguments we specify
    """

    def __init__(self, **kwargs):
        self.args = kwargs


class FakeReactor(object):
    """
    Overrides the reactor behavior, to allow to control delayed callbacks
    """

    def __init__(self):
        self.call_later_cb = None

    def callLater(self, delay, cb):
        self.call_later_callback = cb

    def call_now(self):
        self.call_later_callback()


# Tests ######################################################################

class TableTest(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)

        self.service = CardstoriesService({'db': self.database,
                                           'plugins-confdir': 'CONFDIR',
                                           'plugins-libdir': 'LIBDIR',
                                           'static': 'STATIC'})
        self.service.auth = Mock()
        self.service.startService()

        # Fake an activity plugin to which the table plugin should listen
        self.mock_activity_instance = Mock()
        self.mock_activity_instance.name.return_value = 'activity'
        # Show all players as online
        self.mock_activity_instance.is_player_online.return_value = True

        self.table_instance = table.Plugin(self.service, [self.mock_activity_instance])

        self.mock_activity_instance.listen.assert_called_once_with()
        self.mock_activity_instance.reset_mock()

    def tearDown(self):
        # kill the service we started before the test
        return self.service.stopService()


    @defer.inlineCallbacks
    def add_players_to_game(self, game_id, player_ids):
        sql = "INSERT INTO tabs (player_id, game_id, created) VALUES (%d, %d, datetime('now'))"
        for player_id in player_ids:
            yield self.service.db.runQuery(sql % (player_id, game_id))

    @defer.inlineCallbacks
    def complete_game(self, game_id, owner, player1, player2):
        # Set card
        yield self.service.handle([], {'action': ['set_card'],
                                       'card': [1],
                                       'game_id': [game_id],
                                       'player_id': [owner]})
        # Set sentence
        yield self.service.handle([], {'action': ['set_sentence'],
                                       'sentence': ['SENTENCE'],
                                       'game_id': [game_id],
                                       'player_id': [owner]})
        # Join
        yield self.service.handle([], {'action': ['participate'],
                                       'game_id': [game_id],
                                       'player_id': [player1]})
        yield self.service.handle([], {'action': ['participate'],
                                       'game_id': [game_id],
                                       'player_id': [player2]})

        # Pick
        game, players_ids = yield self.table_instance.get_game_by_id(game_id, player1)
        yield self.service.handle([], {'action': ['pick'],
                                       'game_id': [game_id],
                                       'player_id': [player1],
                                       'card': [game['self'][2][0]]})
        game, players_ids = yield self.table_instance.get_game_by_id(game_id, player2)
        yield self.service.handle([], {'action': ['pick'],
                                       'game_id': [game_id],
                                       'player_id': [player2],
                                       'card': [game['self'][2][0]]})

        # Vote
        yield self.service.handle([], {'action': ['voting'],
                                       'game_id': [game_id],
                                       'owner_id': [game['owner_id']]})

        @defer.inlineCallbacks
        def player_vote(player_id):
            game, players_ids = yield self.table_instance.get_game_by_id(game_id, player_id)
            my_card = game['self'][0]
            board = [x for x in game['board'] if x != my_card]
            yield self.service.handle([], {'action': ['vote'],
                                           'game_id': [game_id],
                                           'player_id': [player_id],
                                           'card': [board[0]]})
        yield player_vote(player1)
        yield player_vote(player2)

        # Complete
        yield self.service.handle([], {'action': ['complete'],
                                       'game_id': [game_id],
                                       'owner_id': [game['owner_id']]})

    @defer.inlineCallbacks
    def test01_no_table(self):
        player_id = 12
        game_id = 59

        # Request for tables should direct the player to create his own game
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': ['undefined'],
                                                 'player_id': [player_id]})
        self.assertEqual(state, [{'game_id': None,
                                  'next_game_id': None,
                                  'next_owner_id': player_id},
                                 [player_id]])

        # Next games of existing games should also ask to create a new game, since we have no table info
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player_id]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player_id},
                                 [player_id]])

    @defer.inlineCallbacks
    def test02_create_game_next(self):
        player1 = 12
        player2 = 78
        player3 = 98

        # Poll to know when a table gets available
        poll = self.table_instance.poll({'game_id': ['undefined'],
                                         'modified': [0]})
        result = yield poll
        modified = result['modified'][0]
        # Start a new poll immediately.
        poll = self.table_instance.poll({'game_id': ['undefined'],
                                         'modified': [modified]})
        # Make sure it doesn't return at once.
        self.assertFalse(poll.called)

        self.assertEqual(modified, self.table_instance.get_modified({'game_id': ['undefined']}))

        # Create first game
        response = yield self.service.handle([], {'action': ['create'],
                                                  'owner_id': [player1]})
        game_id = response['game_id']

        # Poll must return to inform players waiting for an available table
        result = yield poll
        modified = result['modified'][0]

        # Associate all players with the game in the tabs db table.
        sql = "INSERT INTO tabs (player_id, game_id, created) VALUES (%d, %d, datetime('now'))"
        for player_id in [player1, player2, player3]:
            yield self.service.db.runQuery(sql % (player_id, game_id))

        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': ['undefined'],
                                                 'player_id': [player2]})
        self.assertEqual(state, [{'game_id': None,
                                  'next_game_id': game_id,
                                  'next_owner_id': player1},
                                 [player1]])

        # Initial state of the table itself
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player1]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': None},
                                 []])

        # Start a poll on this table to know when the next game will be available there
        poll = self.table_instance.poll({'game_id': [game_id],
                                         'modified': [0]})
        result = yield poll
        modified = result['modified'][0]

        poll = self.table_instance.poll({'game_id': [game_id],
                                         'modified': [modified]})
        self.assertFalse(poll.called)
        self.assertEqual(modified, self.table_instance.get_modified({'game_id': [game_id]}))

        # Complete first game
        yield self.complete_game(game_id, player1, player2, player3)
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player1]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player2},
                                 [player2]])

        # Poll must return to announce the next owner
        result = yield poll
        modified = result['modified'][0]

        poll = self.table_instance.poll({'game_id': [game_id],
                                         'modified': [modified]})
        self.assertFalse(poll.called)

        # Next owner disconnects before creating the game - should chose another player
        def is_player_online(*args, **kw):
            if args[0] == player2:
                return False
            return True
        self.mock_activity_instance.is_player_online.side_effect = is_player_online
        yield self.table_instance.on_activity_notification({'type': 'player_disconnecting',
                                                            'player_id': player2})

        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player1]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player3},
                                 [player3]])

        # Poll must return to announce the next owner
        result = yield poll
        modified = result['modified'][0]

        poll = self.table_instance.poll({'game_id': [game_id],
                                         'modified': [modified]})
        self.assertFalse(poll.called)

        # Next owner closes the tab before creating the game - should choose another player
        yield self.service.remove_tab({'action': ['remove_tab'],
                                       'player_id': [player3],
                                       'game_id': [game_id]})

        # Poll must return to announce the next owner
        result = yield poll
        modified = result['modified'][0]

        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player1]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player1},
                                 [player1]])

        # All players quit - deletes the table
        # Clear the side_effect which otherwise takes precedence over return_value.
        self.mock_activity_instance.is_player_online.side_effect = None
        self.mock_activity_instance.is_player_online.return_value = False
        yield self.table_instance.on_activity_notification({'type': 'player_disconnecting',
                                                            'player_id': player1})
        yield self.table_instance.on_activity_notification({'type': 'player_disconnecting',
                                                            'player_id': player3})

        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player1]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player1},
                                 [player1]])


    @defer.inlineCallbacks
    def test03_disconnect_with_two_tables(self):
        """
        Bug #797 - ValueError: list.remove(x): x not in list (table.py, delete_table)
        """

        player_id = 12

        # Create two tables
        self.assertEqual(len(self.table_instance.tables), 0)

        response = yield self.service.handle([], {'action': ['create'],
                                                  'owner_id': [player_id],})
        game1_id = response['game_id']
        yield self.service.handle([], {'action': ['set_card'],
                                       'card': [1],
                                       'player_id': [player_id],
                                       'game_id': [game1_id]})
        yield self.service.handle([], {'action': ['set_sentence'],
                                       'sentence': ['sentence'],
                                       'player_id': [player_id],
                                       'game_id': [game1_id]})

        response = yield self.service.handle([], {'action': ['create'],
                                       'owner_id': [player_id],})
        game2_id = response['game_id']
        yield self.service.handle([], {'action': ['set_card'],
                                       'card': [1],
                                       'player_id': [player_id],
                                       'game_id': [game2_id]})
        yield self.service.handle([], {'action': ['set_sentence'],
                                       'sentence': ['sentence'],
                                       'player_id': [player_id],
                                       'game_id': [game2_id]})

        self.assertEqual(len(self.table_instance.tables), 2)

        # Players quits - deletes the two tables simulteanously
        self.mock_activity_instance.is_player_online.return_value = False
        yield self.table_instance.on_activity_notification({'type': 'player_disconnecting',
                                                            'player_id': player_id})
        self.assertEqual(len(self.table_instance.tables), 0)

    @defer.inlineCallbacks
    def test04_postprocess(self):
        game_id = 55
        tab1_game_id = 17
        tab2_game_id = 18
        player_id = 77

        mock_request = Mock()
        mock_request.args = {'action': ['state'], 'player_id': [player_id], 'game_id': [game_id], 'type': ['tabs']}

        response = [{'type': 'tabs',
                     'games': [{'id': tab1_game_id, 'state': 'complete'}, {'id': tab2_game_id, 'state': 'complete'}]}]

        def mock_state(args):
            game_id = args['game_id'][0]
            if game_id == tab1_game_id:
                next_game_id = 42
                next_owner_id = player_id
            elif game_id == tab2_game_id:
                next_game_id = None
                next_owner_id = 21

            result = [{'game_id': game_id, 'next_game_id': next_game_id, 'next_owner_id': next_owner_id}, [player_id]]
            return result
        self.table_instance.state = mock_state

        result = yield self.table_instance.postprocess(response, mock_request)

        # During postprocessing, next_owner_id and next_game_id should be added to
        # the response.
        self.assertEqual(result[0]['games'][0]['next_owner_id'], player_id)
        self.assertEqual(result[0]['games'][0]['next_game_id'], 42)
        self.assertEqual(result[0]['games'][1]['next_owner_id'], 21)
        self.assertEqual(result[0]['games'][1]['next_game_id'], None)

        # Make sure things don't fail if response is not of the expected shape.
        yield self.table_instance.postprocess({'type': 'chat'}, mock_request)
        yield self.table_instance.postprocess([[1, 2, {'this': 'test'}]], mock_request)

    @defer.inlineCallbacks
    def test05_close_tab_with_nonexisting_table(self):
        player_id = 43
        game_id = 1123321
        self.assertEqual(len(self.table_instance.tables), 0)
        result = yield self.table_instance.on_tab_closed(player_id, game_id)
        self.assertEqual(result, True)

    @defer.inlineCallbacks
    def test06_next_game_timeout(self):
        owner = 98
        player1 = 12
        player2 = 78

        # Create game
        response = yield self.service.handle([], {'action': ['create'],
                                                  'owner_id': [owner]})
        game_id = response['game_id']

        sql = "INSERT INTO tabs (player_id, game_id, created) VALUES (%d, %d, datetime('now'))"
        for player_id in [owner, player1, player2]:
            yield self.service.db.runQuery(sql % (player_id, game_id))

        # Change the next game timeout from the default to 0.2 seconds for the test.
        table = self.table_instance.game2table[game_id]
        table.NEXT_GAME_TIMEOUT = 0.2

        # Complete the game
        yield self.complete_game(game_id, owner, player1, player2)

        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player1]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player1},
                                 [player1]])

        # Start a poll on this table to know when the next owner will change.
        poll = self.table_instance.poll({'game_id': [game_id],
                                         'modified': [table.get_modified()]})

        result = yield poll

        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player1]})
        # Next owner took too long to create the game,
        # so player2 was chosen as the "new" next owner.
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player2},
                                 [player2]])

        # Cancel the timers, so that the test runner doesn't complain
        # about a "dirty" reactor.
        table.stop_timer(table.next_game_timer)

    @defer.inlineCallbacks
    def test07_next_game_timeout_after_game_created(self):
        owner = 57
        player1 = 123
        player2 = 334

        # Create first game
        response = yield self.service.handle([], {'action': ['create'],
                                                  'owner_id': [owner]})
        game_id = response['game_id']

        self.add_players_to_game(game_id, [owner, player1, player2])

        # Change the next game timeout from the default to 0.2 seconds for the test.
        table = self.table_instance.game2table[game_id]
        table.NEXT_GAME_TIMEOUT = 0.2

        # Complete the game
        yield self.complete_game(game_id, owner, player1, player2)

        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player1]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player1},
                                 [player1]])

        # player1 is the next owner, let him create the next game.
        # We will let him wait long enough so that the timer kicks in and
        # gives another player a chance to be next owner.
        response = yield self.service.handle([], {'action': ['create'],
                                                  'owner_id': [player1],
                                                  'previous_game_id': [game_id]})
        new_game_id = response['game_id']

        self.add_players_to_game(new_game_id, [owner, player1, player2])

        # Start a poll on this table to know when another player is chosen.
        # Not sure why I need to yield on the poll twice :-(
        poll = self.table_instance.poll({'game_id': [new_game_id],
                                         'modified': [0]})
        result = yield poll
        modified = result['modified'][0]
        poll = self.table_instance.poll({'game_id': [new_game_id],
                                         'modified': [modified]})
        result = yield poll
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [new_game_id],
                                                 'player_id': [owner]})

        # Next owner took too long to create the game,
        # so player2 was chosen as the "new" next owner.
        # This can be seen when inquiring about table
        # from the new, pending game.
        self.assertEqual(state, [{'game_id': new_game_id,
                                  'next_game_id': None, # player 2 didn't create the next game yet, so it is None
                                  'next_owner_id': player2}, # player2 is now the next owner
                                 [player2]])

        # The same result should be seen when inquiring about the table from the old (previous) game,
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [player2]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player2},
                                 [player2]])

        # Player 2 creates a new game
        response = yield self.service.handle([], {'action': ['create'],
                                                  'owner_id': [player2],
                                                  'previous_game_id': [new_game_id]})
        newest_game_id = response['game_id']

        # Check the state now.
        # At this point, player1's and player2's games are both pending.
        # Depending on from which game you inquire about it, you should see
        # different results.

        # Looking from the first (and still current) game, the user should be
        # pointed to the newest pending game:
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [owner]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': newest_game_id,
                                  'next_owner_id': player2},
                                 [player2]])

        # Looking from player1's pending game, the table should report the
        # new owner (player2), but not the new game yet, because it's still pending:
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [new_game_id],
                                                 'player_id': [owner]})
        self.assertEqual(state, [{'game_id': new_game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player2},
                                 [player2]])

        # Looking from player2's pending game, we should see the same results:
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [newest_game_id],
                                                 'player_id': [owner]})
        self.assertEqual(state, [{'game_id': newest_game_id,
                                  'next_game_id': None,
                                  'next_owner_id': player2},
                                 [player2]])

        # Let player1 finish creating the game now by setting the card and sentence.
        # player1's game should be promoted as the next game of the table and every
        # of the above requests should not point to it.
        # Set card
        yield self.service.handle([], {'action': ['set_card'],
                                       'card': [1],
                                       'game_id': [new_game_id],
                                       'player_id': [player1]})
        # Set sentence
        yield self.service.handle([], {'action': ['set_sentence'],
                                       'sentence': ['SENTENCE'],
                                       'game_id': [new_game_id],
                                       'player_id': [player1]})

        # Looking from previous game:
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [game_id],
                                                 'player_id': [owner]})
        self.assertEqual(state, [{'game_id': game_id,
                                  'next_game_id': new_game_id,
                                  'next_owner_id': player1},
                                 [player1]])

        # Looking from player1's game, which was promoted:
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [new_game_id],
                                                 'player_id': [owner]})
        self.assertEqual(state, [{'game_id': new_game_id,
                                  'next_game_id': None,
                                  'next_owner_id': None},
                                 []])
        # The game should still be part of the same old table.
        table2 = self.table_instance.game2table[new_game_id]
        self.assertEqual(table2, table)

        # Looking from player2's game, which was discarded from this table,
        # the game should be spun off into a totally new table.
        state = yield self.table_instance.state({'type': ['table'],
                                                 'game_id': [newest_game_id],
                                                 'player_id': [owner]})
        self.assertEqual(state, [{'game_id': newest_game_id,
                                  'next_game_id': None,
                                  'next_owner_id': None},
                                 []])
        # The game should be part of its own brand new table.
        table3 = self.table_instance.game2table[newest_game_id]
        self.assertNotEqual(table3, table)


    @defer.inlineCallbacks
    def test09_next_owner_id_race_condition(self):
        owner = 11
        player1 = 12
        player2 = 13

        # Create the game.
        response = yield self.service.handle([], {'action': ['create'],
                                                  'owner_id': [owner]})
        game_id = response['game_id']
        self.add_players_to_game(game_id, [owner, player1, player2])
        # Complete the game.
        yield self.complete_game(game_id, owner, player1, player2)

        table = self.table_instance.game2table[game_id]

        self.test_done = False

        self.counter = 0

        def listener(args):
            if not self.test_done:
                self.counter += 1
                modified = args['modified'][0]
                table.poll({'modified': [modified]}).addCallback(listener)
            return args

        modified = table.get_modified()
        poll = table.poll({'modified': [modified]}).addCallback(listener)

        d1 = table.update_next_owner_id()
        d2 = table.update_next_owner_id()
        d3 = table.update_next_owner_id()

        d = defer.DeferredList([d1, d2, d3])

        # Wait for all three update operations to finish...
        yield d
        # ...and then wait for the next_owner change to be dispatched by the poll.
        yield poll

        self.assertEquals(self.counter, 1)

        # Break the listen loop so that the test runner doesn't complain
        # about a dirty reactor.
        self.test_done = True
        table.touch({})
        # For the same reason cancel the next_game_timer.
        table.stop_timer(table.next_game_timer)


def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(TableTest))

    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

