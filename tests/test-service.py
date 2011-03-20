#
# Copyright (C) 2011 Dachary <loic@dachary.org>
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
sys.path.insert(0, "..") # so that for M-x pdb works
import os
import sqlite3

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer, reactor
from twisted.web import server, resource, http

from cardstories.service import CardstoriesService

class CardstoriesServiceTestInit(unittest.TestCase):

    def test00_startService(self):
        database = 'test.sqlite'
        service = CardstoriesService({'db': database})
        self.assertFalse(os.path.exists(database))
        service.startService()
        self.assertTrue(os.path.exists(database))

class CardstoriesServiceTest(unittest.TestCase):

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

class CardstoriesServiceTestRun(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)

    def tearDown(self):
        os.unlink(self.database)

    def test00_run(self):
        self.service = CardstoriesService({'db': self.database, 'loop': 2})
        d = self.service.startService()
        d.addCallback(lambda result: self.assertTrue(result))
        return d

class CardstoriesServiceTestCreateGet(CardstoriesServiceTest):

    def test01_create(self):
        card = '1'
        sentence = 'sentence'
        d = self.service.create({ 'card': [card], 'sentence': [sentence]})
        def check(result):
            c = self.db.cursor()
            c.execute("SELECT * FROM games")
            rows = c.fetchall()
            self.assertEquals(1, len(rows))
            self.assertEquals(card, rows[0][1])
            self.assertEquals(sentence, rows[0][2])
            c.close()
        d.addCallback(check)
        return d

    @defer.inlineCallbacks
    def test02_get(self):
        card1 = 'CARD1'
        yield self.service.create({ 'card': [card1]})
        card2 = 'CARD2'
        yield self.service.create({ 'card': [card2]})
        yield self.service.db.runOperation("UPDATE cards SET alive = datetime('now') WHERE card = '%s'" % card1)
        yield self.service.db.runOperation("UPDATE cards SET alive = datetime('now','+1 hour') WHERE card = '%s'" % card2)
        rows = yield self.service.get()
        self.assertEquals(card2, rows['rows'][0][1])
        self.assertEquals(card1, rows['rows'][1][1])


class CardstoriesServiceTestPing(CardstoriesServiceTest):

    def setUp(self):
        CardstoriesServiceTest.setUp(self)

        self.url_behaviour = 'OK'

        class R(resource.Resource):
            isLeaf = True
            def render_GET(Rself, request):
                if self.url_behaviour == 'OK':
                    if request.path == '/':
                        return 'CONTENT'
                    else:
                        request.setResponseCode(http.NOT_FOUND)
                        return 'NOT OK 404'
                elif self.url_behaviour == '500':
                    request.setResponseCode(http.INTERNAL_SERVER_ERROR)
                    return 'NOT OK 500'
                elif self.url_behaviour == 'timeout':
                    return server.NOT_DONE_YET

        self.server = reactor.listenTCP(0, server.Site(R()), interface='127.0.0.1')
        self.port = self.server.getHost().port

    def tearDown(self):
        CardstoriesServiceTest.tearDown(self)
        return self.server.stopListening()

    @defer.inlineCallbacks
    def test00_ping_ok(self):
        url = 'http://127.0.0.1:%d' % self.port
        yield self.service.submit({ 'url': [url]})
        rows = yield self.service.get()
        self.assertEquals('down', rows['rows'][0][2])
        self.assertEquals(None, rows['rows'][0][3]) # alive
        self.assertEquals(None, rows['rows'][0][4]) # checked
        # URL responds
        self.url_behaviour = 'OK'
        content = yield self.service.ping(1, url)
        self.assertEquals('OK 1', content)
        rows = yield self.service.get()
        self.assertEquals('up', rows['rows'][0][2])
        self.assertEquals(rows['rows'][0][3], rows['rows'][0][4]) # alive == checked
        
    @defer.inlineCallbacks
    def test01_ping_500(self):
        url = 'http://127.0.0.1:%d' % self.port
        yield self.service.submit({ 'url': [url]})
        yield self.service.db.runOperation("UPDATE urls SET checked = datetime('now','-1 hour'), alive = datetime('now','-1 hour'), state = 'up'")
        rows = yield self.service.get()
        self.assertEquals('up', rows['rows'][0][2])
        self.assertEquals(rows['rows'][0][3], rows['rows'][0][4]) # alive == checked
        rows = yield self.service.db.runQuery("SELECT * FROM urls WHERE checked > alive")
        self.assertEquals([], rows)
        # URL fails with HTTP error 500
        self.url_behaviour = '500'
        d = self.service.ping(1, url)
        def error500(reason):
            self.assertEquals('500', reason.value.status)
            return True
        d.addErrback(error500)
        yield d
        rows = yield self.service.get()
        self.assertEquals('down', rows['rows'][0][2])
        rows = yield self.service.db.runQuery("SELECT * FROM urls WHERE checked > alive")
        self.assertEquals('down', rows[0][2])

    @defer.inlineCallbacks
    def test02_ping_timeout(self):
        url = 'http://127.0.0.1:%d' % self.port
        yield self.service.submit({ 'url': [url]})
        yield self.service.db.runOperation("UPDATE urls SET state = 'up'")
        # URL fails because the URL timesout
        self.service.settings['ping-timeout'] = 0.1
        self.url_behaviour = 'timeout'
        d = self.service.ping(1, url)
        def timeout(reason):
            self.assertTrue(isinstance(reason.value, defer.TimeoutError))
            return True
        d.addErrback(timeout)
        yield d
        rows = yield self.service.get()
        self.assertEquals('down', rows['rows'][0][2])

    @defer.inlineCallbacks
    def test03_pings(self):
        parallel_pings = 2
        self.service.settings['parallel-pings'] = parallel_pings
        url_good = 'http://127.0.0.1:%d' % self.port
        yield self.service.submit({ 'url': [url_good]})
        url_bad = 'http://127.0.0.1:%d/not_found' % self.port
        for i in ('1','2','3'):
            yield self.service.submit({ 'url': [url_bad + i]})
        # pass 1
        results = yield self.service.pings()
        self.assertEquals(parallel_pings, len(results))
        self.assertEquals('OK 1', results[0])
        self.assertEquals((2, str(http.NOT_FOUND)), (results[1][0], results[1][1].value.status))
        # pass 2
        results = yield self.service.pings()
        self.assertEquals(parallel_pings, len(results))
        self.assertEquals((3, str(http.NOT_FOUND)), (results[0][0], results[0][1].value.status))
        self.assertEquals((4, str(http.NOT_FOUND)), (results[1][0], results[1][1].value.status))
        # pass 3
        results = yield self.service.pings()
        self.assertEquals(parallel_pings, len(results))
        self.assertEquals('OK 1', results[0])
        self.assertEquals((2, str(http.NOT_FOUND)), (results[1][0], results[1][1].value.status))

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesServiceTestInit))
    suite.addTest(loader.loadClass(CardstoriesServiceTestCreateGet))
    suite.addTest(loader.loadClass(CardstoriesServiceTestRun))

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
# compile-command: "python-coverage -e ; PYTHONPATH=.. python-coverage -x test-service.py ; python-coverage -m -a -r ../cardstories/service.py"
# End:
