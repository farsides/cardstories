# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Loic Dachary <loic@dachary.org>
# Copyright (C) 2011-2012 Farsides <contact@farsides.com>
#
# Authors:
#          Loic Dachary <loic@dachary.org>
#          Xavier Antoviaque <xavier@antoviaque.org>
#          Adolfo R. Brandes <arbrandes@gmail.com>
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
sys.path.insert(0, os.path.abspath("../..")) # so that for M-x pdb works
import sqlite3

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer

from plugins.auth.auth import Plugin

class FakeService:

    def __init__(self, settings):
        self.settings = settings

class AuthTestInit(unittest.TestCase):

    def test00_create(self):
        auth = Plugin(FakeService({'plugins-libdir': '.'}), [])
        self.assertTrue(os.path.exists(auth.database))

class AuthTest(unittest.TestCase):

    def setUp(self):
        self.auth = Plugin(FakeService({'plugins-libdir': '.'}), [])
        self.db = sqlite3.connect(self.auth.database)

    def tearDown(self):
        self.db.close()
        os.unlink(self.auth.database)

    @defer.inlineCallbacks
    def test02_create_emails(self):
        emails = [u'owner@foo.com', u'player1@foo.com', u'player']
        ids = yield self.auth.get_players_ids(emails, create=True)
        self.assertEquals([1, 2, 3], ids)

    @defer.inlineCallbacks
    def test03_get_name(self):
        name = yield self.auth.get_player_name(3)
        self.assertEquals("Player 3", name)

    @defer.inlineCallbacks
    def test04_get_player_avatar_url(self):
        avatar_url = yield self.auth.get_player_avatar_url('3')
        self.assertEquals('/static/css/images/avatars/default/3.jpg', avatar_url)


def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(AuthTestInit))
    suite.addTest(loader.loadClass(AuthTest))

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
# compile-command: "python-coverage -e ; PYTHONPATH=../.. python-coverage -x test_auth.py ; python-coverage -m -a -r auth.py"
# End:
