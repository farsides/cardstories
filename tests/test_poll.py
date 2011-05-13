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

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer, base
from twisted.python import failure

from cardstories import poll

base.DelayedCall.debug = True

class PollableTest(unittest.TestCase):

    @defer.inlineCallbacks
    def test00_poll(self):
        timeout = 100
        p = poll.pollable(timeout)
        # if the pollable has been recently modified, the 
        # deferred is triggered immediately
        self.assertEquals([], p.pollers)
        args = { 'modified': [0] }
        result = yield p.poll(args)
        self.assertEquals(result['modified'][0], p.modified)
        # the deferred times out
        args = { 'modified': [p.modified] }
        p.timeout = 0.01
        self.assertEquals([], p.pollers)
        d = p.poll(args)
        def check(result):
            self.assertTrue(args.has_key('timeout'))
            result['ok'] = [True]
            return result
        d.addCallback(check)
        self.assertEquals(1, len(p.pollers))
        self.assertFalse(args.has_key('timeout'))
        result = yield d
        self.assertEquals([], p.pollers)
        self.assertTrue(result.has_key('timeout'))
        self.assertTrue(result['ok'])
        # the deferred is triggered
        p.timeout = 1000000000
        args = { 'modified': [p.modified] }
        d = p.poll(args)
        def check(result):
            self.assertEquals(result['modified'][0], p.modified)
            self.assertFalse(result.has_key('timeout'))
            self.assertTrue(result.has_key('active_timer'))
            result['ok'] = [True]
            return result
        d.addCallback(check)
        d.callback({})
        result = yield d
        self.assertTrue(result['ok'])
        # the deferred error is triggered
        args = { 'modified': [p.modified] }
        d = p.poll(args)
        def check(reason):
            self.assertTrue(reason.active_timer)
            return {'ok': [True]}
        d.addErrback(check)
        d.errback(failure.Failure(Exception()))
        result = yield d
        self.assertTrue(result['ok'])

    @defer.inlineCallbacks
    def test01_touch(self):
        timeout = 100
        p = poll.pollable(timeout)
        p.modified -= 1000
        d = p.poll({ 'modified': [p.modified] })
        def check(result):
            # pollers must be reset before the callbacks are triggered
            # so that they can register new pollers without interfering
            self.assertEquals(0, len(p.pollers))
            return result
        d.addCallback(check)
        args = { 'ok': [True] }
        self.assertEquals(1, len(p.pollers))
        r = p.touch(args)
        self.assertEquals(r['modified'][0], p.modified)
        self.assertEquals(0, len(p.pollers))
        result = yield d
        self.assertTrue(result['ok'])
        self.assertEquals(result['modified'][0], p.modified)

    def test02_destroy(self):
        timeout = 100
        p = poll.pollable(timeout)
        p.modified -= 1000
        d = p.poll({ 'modified': [p.modified] })
        def check(result):
            self.assertEquals(None, result)
            return result
        d.addCallback(check)
        p.destroy()
        return d

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(PollableTest))

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
# compile-command: "python-coverage -e ; PYTHONPATH=.. python-coverage -x test_poll.py ; python-coverage -m -a -r ../cardstories/poll.py"
# End:
