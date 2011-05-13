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

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer

from cardstories.auth import Auth

class AuthTestInit(unittest.TestCase):

    def test00_create(self):
        database = 'test.sqlite'
        auth = Auth({'auth-db': database})
        self.assertTrue(os.path.exists(database))

class AuthTest(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)
        self.auth = Auth({'auth-db': self.database})
        self.db = sqlite3.connect(self.database)

    def tearDown(self):
        self.db.close()
        os.unlink(self.database)

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
                                   ] }
        result_out = yield self.auth.postprocess(result_in)
        self.assertEquals(result_out, { 'players': [ [ player ],
                                                     [ owner ] ] })
        

    @defer.inlineCallbacks
    def test01_invite(self):
        mails = [ u'mail1@foo.com', u'mail2@foo.com' ]
        game_id = 20
        class request:
            def __init__(self):
                self.args = { 'player_id': mails,
                              'game_id': [ game_id ],
                              'action': [ 'invite' ] }
        host = 'HOST'
        self.auth.settings['mail-host'] = host
        sender = 'FROM'
        self.auth.settings['mail-from'] = sender
        subject = 'SUBJECT'
        self.auth.settings['mail-subject'] = subject
        body = '%(player_id)s %(game_id)s'
        self.auth.settings['mail-body'] = body
        request1 = request()
        result_in = 'RESULT'
        self.auth.count = 0
        def sendmail(_host, _sender, _mail, payload):
            self.assertEqual(_host, host)
            self.assertEqual(_sender, sender)
            self.assertEqual(_mail, mails[self.auth.count])
            self.failUnlessSubstring(body % { 'player_id': mails[self.auth.count],
                                              'game_id': game_id }, payload)
            self.auth.count += 1
            return defer.succeed(True)
        self.auth.sendmail = sendmail
        result_out = yield self.auth.preprocess(result_in, request1)

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
# compile-command: "python-coverage -e ; PYTHONPATH=.. python-coverage -x test_auth.py ; python-coverage -m -a -r ../cardstories/auth.py"
# End:
