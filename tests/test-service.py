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
        self.service = CardstoriesService({'db': self.database, 'loop': 2, 'click': 0.1})
        d = self.service.startService()
        d.addCallback(lambda result: self.assertTrue(result))
        return d

class CardstoriesServiceTest(CardstoriesServiceTest):

    def test01_create(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        d = self.service.create({ 'card': [card],
                                  'sentence': [sentence],
                                  'owner_id': [owner_id]})
        def check(result):
            c = self.db.cursor()
            c.execute("SELECT * FROM games")
            rows = c.fetchall()
            self.assertEquals(1, len(rows))
            self.assertEquals(result['game_id'], rows[0][0])
            self.assertEquals(owner_id, rows[0][1])
            one_player = 1
            self.assertEquals(one_player, rows[0][2])
            self.assertEquals(sentence, rows[0][3])
            self.assertFalse(chr(card) in rows[0][4])
            self.assertEquals(chr(card), rows[0][5])
            c.execute("SELECT cards FROM player2game WHERE game_id = %d AND player_id = %d" %  ( result['game_id'], owner_id ))
            rows = c.fetchall()
            self.assertEquals(1, len(rows))
            self.assertEquals(chr(card), rows[0][0])
            c.close()
        d.addCallback(check)
        return d

    @defer.inlineCallbacks
    def test02_participate(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        c = self.db.cursor()
        c.execute("SELECT LENGTH(cards) FROM games WHERE id = %d" % game['game_id'])
        cards_length = c.fetchone()[0]
        player_id = 23
        participation = yield self.service.participate({ 'player_id': [player_id],
                                                         'game_id': [game['game_id']] })
        self.assertEquals({}, participation)
        c.execute("SELECT LENGTH(cards) FROM games WHERE id = %d" % game['game_id'])
        self.assertEquals(cards_length - self.service.CARDS_PER_PLAYER, c.fetchone()[0])
        c.execute("SELECT LENGTH(cards) FROM player2game WHERE game_id = %d AND player_id = %d" % ( game['game_id'], player_id ))
        self.assertEquals(self.service.CARDS_PER_PLAYER, c.fetchone()[0])
        c.close()

    @defer.inlineCallbacks
    def test03_player2game(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        player_id = 23
        yield self.service.participate({ 'player_id': [player_id],
                                         'game_id': [game['game_id']] })
        player = yield self.service.player2game({ 'player_id': [player_id],
                                                  'game_id': [game['game_id']] })
        self.assertEquals(self.service.CARDS_PER_PLAYER, len(player['cards']))
        self.assertEquals(None, player['vote'])
        self.assertEquals(u'n', player['win'])

    @defer.inlineCallbacks
    def test03_pick(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        player2card = {}
        for player_id in ( 16, 17 ):
            yield self.service.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.service.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            player2card[player_id] = player['cards'][0]
            yield self.service.pick({ 'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [ player2card[player_id] ] })
        
        c = self.db.cursor()
        for player_id in ( 16, 17 ):
            c.execute("SELECT picked FROM player2game WHERE game_id = %d AND player_id = %d" % ( game['game_id'], player_id ))
            self.assertEquals(player2card[player_id], ord(c.fetchone()[0]))
        c.close()
            
    @defer.inlineCallbacks
    def test04_voting(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        player2card = {}
        for player_id in ( 16, 17 ):
            yield self.service.participate({ 'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.service.player2game({ 'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            player2card[player_id] = player['cards'][0]
            yield self.service.pick({ 'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [ player2card[player_id] ] })
        
        yield self.service.voting({ 'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })
        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % ( game['game_id'] ))
        self.assertEquals('', c.fetchone()[0])
        c.close()
            
def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesServiceTestInit))
    suite.addTest(loader.loadClass(CardstoriesServiceTest))
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
