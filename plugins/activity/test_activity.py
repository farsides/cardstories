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
from plugins.activity import activity


# Classes ####################################################################

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

class ActivityTest(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)

        self.service = CardstoriesService({'db': self.database,
                                           'plugins-confdir': 'CONFDIR',
                                           'plugins-libdir': 'LIBDIR',
                                           'static': 'STATIC'
                                           })
        self.service.startService()

        # Don't actually make delayed calls, but allow tests to call them
        self.default_reactor = activity.reactor.callLater
        self.activity_reactor = FakeReactor()
        activity.reactor = self.activity_reactor

        self.activity_instance = activity.Plugin(self.service, [])

    def tearDown(self):
        activity.reactor = self.default_reactor

        # kill the service we started before the test
        return self.service.stopService()

    @defer.inlineCallbacks
    def check_online_players(self, online_players):
        """
        Check that the players currently online are the ones (and only the ones) in the list online_players_ids
        """

        state = yield self.activity_instance.state([])
        self.assertEqual(state[0]['online_players'], online_players)

        for player_id in online_players.keys():
            is_online = self.activity_instance.is_player_online(player_id)
            self.assertTrue(is_online, "Player id %d is not online" % player_id)

    @defer.inlineCallbacks
    def test01_online_offline(self):
        player_id = 12

        # No player initially
        yield self.check_online_players({})

        # Player going online
        on_event_mock = Mock()
        self.activity_instance.listen().addCallback(on_event_mock)
        self.activity_instance.on_service_notification({'type': 'poll_start', 'player_id': player_id})

        on_event_mock.assert_called_once_with({'type': 'player_connecting', 'player_id': player_id})
        on_event_mock.reset_mock()
        self.activity_instance.listen().addCallback(on_event_mock)

        yield self.check_online_players({player_id: {'active_polls': 1} })

        # Player dropping poll
        self.activity_instance.on_service_notification({'type': 'poll_end', 'player_id': player_id})
        self.assertEqual(on_event_mock.call_count, 0)
        yield self.check_online_players({player_id: {'active_polls': 0} })

        # Player starting another poll quickly enough
        self.activity_instance.on_service_notification({'type': 'poll_start', 'player_id': player_id})
        self.assertEqual(on_event_mock.call_count, 0)
        yield self.check_online_players({player_id: {'active_polls': 1} })

        # Player dropping poll again, this time for good (going offline)
        self.activity_instance.on_service_notification({'type': 'poll_end', 'player_id': player_id})
        self.assertEqual(on_event_mock.call_count, 0)
        self.activity_reactor.call_now()
        # Second call should not have any effect (several delayed call can happen concurrently)
        self.activity_reactor.call_now()

        on_event_mock.assert_called_once_with({'type': 'player_disconnecting', 'player_id': player_id})
        yield self.check_online_players({})


def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(ActivityTest))

    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)


