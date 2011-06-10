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
    def test00_translate(self):
        player = u'player'
        invited = u'invited'
        owner = u'owner'
        class request:
            def __init__(self):
                self.args = { 'player_id': [ player, invited ], 'owner_id': [ owner ] }
        request1 = request()
        result_in = 'RESULT'
        result_out = yield self.auth.preprocess(result_in, request1)
        self.assertEquals(result_in, result_out)
        self.assertEquals(int, type(request1.args['player_id'][0]))
        self.assertEquals(int, type(request1.args['player_id'][1]))
        self.assertEquals(int, type(request1.args['owner_id'][0]))
        self.assertNotEquals(request1.args['player_id'], request1.args['owner_id'])
        request2 = request()
        result_in = 'RESULT'
        result_out = yield self.auth.preprocess(result_in, request2)
        self.assertEquals(request1.args['player_id'][0], request2.args['player_id'][0])
        self.assertEquals(request1.args['player_id'][1], request2.args['player_id'][1])
        self.assertEquals(request1.args['owner_id'][0], request2.args['owner_id'][0])
        c = self.db.cursor()
        c.execute("SELECT id FROM players")
        self.assertEquals([(1,),(2,),(3,)], c.fetchall())

        result_in = { 'players': [ [ request1.args['player_id'][0] ],
                                   [ request1.args['owner_id'][0] ]
                                   ],
                      'invited': [ request1.args['player_id'][0] ] }
        result_out = yield self.auth.postprocess(result_in)
        self.assertEquals(result_out, { 'players': [ [ player ],
                                                     [ owner ] ],
                                        'invited': [ player ]})
        

    @defer.inlineCallbacks
    def test02_accent(self):
        player = 'pl\xc3\xa1y\xe1\xba\xbdr'
        invited = 'invited'
        owner = '\xc3\xad\xc3\xb1vit\xc3\xa9d'
        class request:
            def __init__(self):
                self.args = { 'player_id': [ player, invited ], 'owner_id': [ owner ] }
        request1 = request()
        result_in = 'RESULT'
        result_out = yield self.auth.preprocess(result_in, request1)
        self.assertEquals(result_in, result_out)
        self.assertEquals(int, type(request1.args['player_id'][0]))
        self.assertEquals(int, type(request1.args['player_id'][1]))
        self.assertEquals(int, type(request1.args['owner_id'][0]))
        self.assertNotEquals(request1.args['player_id'], request1.args['owner_id'])
        request2 = request()
        result_in = 'RESULT'
        result_out = yield self.auth.preprocess(result_in, request2)
        self.assertEquals(request1.args['player_id'][0], request2.args['player_id'][0])
        self.assertEquals(request1.args['player_id'][1], request2.args['player_id'][1])
        self.assertEquals(request1.args['owner_id'][0], request2.args['owner_id'][0])
        c = self.db.cursor()
        c.execute("SELECT id FROM players")
        self.assertEquals([(1,),(2,),(3,)], c.fetchall())

        result_in = { 'players': [ [ request1.args['player_id'][0] ],
                                   [ request1.args['owner_id'][0] ]
                                   ] }
        result_out = yield self.auth.postprocess(result_in)
        self.assertEquals(result_out, { 'players': [ [ unicode(player, 'utf-8') ],
                                                     [ unicode(owner, 'utf-8') ] ] })


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
