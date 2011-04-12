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
import os
sys.path.insert(0, os.path.abspath("..")) # so that for M-x pdb works
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
        return service.stopService()

    @defer.inlineCallbacks
    def test01_load(self):
        database = 'test.sqlite'
        if os.path.exists(database):
            os.unlink(database)

        service = CardstoriesService({'db': database})
        self.assertFalse(os.path.exists(database))
        service.startService()
        self.assertTrue(os.path.exists(database))
        yield service.stopService()

        game_id = 100
        db = sqlite3.connect(database)
        c = db.cursor()
        c.execute("INSERT INTO games (id) VALUES (%d)" % game_id)
        db.commit()
        db.close()

        service = CardstoriesService({'db': database})
        service.startService()
        self.assertEquals(service.games[game_id].id, game_id)
        yield service.stopService()

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

class CardstoriesServiceTestHandle(CardstoriesServiceTest):

    def test01_required(self):
        self.assertTrue(CardstoriesService.required({ 'key1': ['a'],
                                                      'key2': ['b'] }, 'method', 'key1'))
        
        self.failUnlessRaises(UserWarning, CardstoriesService.required, { }, 'method', 'key1')

    @defer.inlineCallbacks
    def test02_handle(self):
        for action in self.service.ACTIONS:
            result = yield self.service.handle({ 'action': [action] })
            self.failUnlessSubstring(action, result['error'])
            self.failUnlessSubstring('must be given', result['error'])

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
            self.assertEquals(self.service.games[result['game_id']].get_id(), result['game_id'])
            c.close()
        d.addCallback(check)
        return d

    def test02_game_proxy(self):
        game_id = 100
        for action in self.service.ACTIONS:
            getattr(self.service, action)
        #
        # checks if the required arguments are present
        #
        caught = False
        try:
            self.service.game_proxy({'action': 'participate'})
        except UserWarning, e:
            caught = True
            self.failUnlessSubstring('must be given a game_id', e.args[0])
        self.assertTrue(caught)
        #
        # checks if the game actually exists
        #
        caught = False
        try:
            self.service.game_proxy({'game_id': [game_id]})
        except UserWarning, e:
            caught = True
            self.failUnlessSubstring('does not exist', e.args[0])
        self.assertTrue(caught)
        #
        #
        # route to the game function
        #
        class Game:
            def participate(self, args):
                self.participated = True
        self.service.games[game_id] = Game()
        self.service.game_proxy({ 'action': ['participate'],
                                  'game_id': [game_id] })
        self.assertTrue(self.service.games[game_id].participated)
        
    @defer.inlineCallbacks
    def test03_complete(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        for player_id in ( 16, 17 ):
            yield self.service.participate({ 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [game['game_id']] })
            player = yield self.service.player2game({ 'action': ['player2game'],
                                                      'player_id': [player_id],
                                                      'game_id': [game['game_id']] })
            card = player['cards'][0]
            yield self.service.pick({ 'action': ['pick'],
                                      'player_id': [player_id],
                                      'game_id': [game['game_id']],
                                      'card': [card] })
        
        yield self.service.voting({ 'action': ['voting'],
                                    'game_id': [game['game_id']],
                                    'owner_id': [owner_id] })

        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % game['game_id'])
        board = c.fetchone()[0]
        winner_id = 16
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [game['game_id']],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = 17
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [game['game_id']],
                                  'player_id': [loser_id],
                                  'card': [120] })
        self.assertTrue(self.service.games.has_key(game['game_id']))
        yield self.service.complete({ 'action': ['complete'],
                                      'game_id': [game['game_id']],
                                      'owner_id': [owner_id] })
        self.assertFalse(self.service.games.has_key(game['game_id']))
            
    @defer.inlineCallbacks
    def test04_game(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        
        game_info = yield self.service.game({ 'game_id': [game['game_id']] })
        self.assertEquals(game['game_id'], game_info['id'])
        # if there is no in core representation of the game, 
        # a temporary one is created
        del self.service.games[game_info['id']]
        game_info = yield self.service.game({ 'game_id': [game['game_id']] })
        self.assertEquals(game['game_id'], game_info['id'])

    @defer.inlineCallbacks
    def test05_lobby(self):
        player1 = 10
        player2 = 11
        game1 = 100
        sentence1 = 'SENTENCE1'
        game2 = 101
        sentence2 = 'SENTENCE2'
        game3 = 102
        sentence3 = 'SENTENCE3'
        game4 = 103
        sentence4 = 'SENTENCE4'
        c = self.db.cursor()
        # in progress
        c.execute("INSERT INTO games ( id, owner_id, sentence, state, created ) VALUES ( %d, %d, '%s', 'invitation', '2011-02-01' )" % ( game1, player2, sentence1 )) 
        c.execute("INSERT INTO invitations ( player_id, game_id ) VALUES ( %d, %d )" % ( player1, game1 ))
        c.execute("INSERT INTO player2game ( player_id, game_id ) VALUES ( %d, %d )" % ( player2, game1 ))

        c.execute("INSERT INTO games ( id, owner_id, sentence, state, created ) VALUES ( %d, %d, '%s', 'invitation', '2011-05-01' )" % ( game2, player1, sentence2 )) 
        c.execute("INSERT INTO player2game ( player_id, game_id, win ) VALUES ( %d, %d, 'n' )" % ( player1, game2 ))
        # complete
        c.execute("INSERT INTO games ( id, owner_id, sentence, state, created ) VALUES ( %d, %d, '%s', 'complete', '2011-03-01' )" % ( game3, player1, sentence3 )) 
        c.execute("INSERT INTO player2game ( player_id, game_id, win ) VALUES ( %d, %d, 'y' )" % ( player1, game3 ))

        c.execute("INSERT INTO games ( id, owner_id, sentence, state, created ) VALUES ( %d, %d, '%s', 'complete', '2011-06-01' )" % ( game4, player2, sentence4 )) 
        c.close()
        self.db.commit()
        #
        # Show all games, in progress, with wins from player2.
        #
        result = yield self.service.lobby({ 'in_progress': ['true'],
                                            'player_id': [player2] })
        # game2 shows before game1 because it is created before
        self.assertEquals(result, {
                #         player2 does not participate in game2
                'games': [(101, u'SENTENCE2', u'invitation', 0, u'2011-05-01'),
                #         player2 participates in game1 and is the author
                          (100, u'SENTENCE1', u'invitation', 1, u'2011-02-01')],
                #         player2 did not yet win game1
                'win': {100: u'n'}
                })

        #
        # Show player2 games, in progress, with wins from player2.
        #
        result = yield self.service.lobby({ 'in_progress': ['true'],
                                            'player_id': [player2],
                                            'my': ['true'] })
        self.assertEquals(result, {
                #         player2 participates in game1 and is the author
                'games': [(100, u'SENTENCE1', u'invitation', 1, u'2011-02-01')],
                #         player2 does not participate in game2 therefore it is not shown
                #         player2 did not yet win game1
                'win': {100: u'n'}
                })

        #
        # Show all games, complete, with wins from player1.
        #
        result = yield self.service.lobby({ 'in_progress': ['false'],
                                            'player_id': [player1] })
        # game4 shows before game3 because it is created before
        self.assertEquals(result, {
                #         player1 did not participate in game3
                'games': [(103, u'SENTENCE4', u'complete', 0, u'2011-06-01'),
                #         player1 participated in game3 and was the author
                          (102, u'SENTENCE3', u'complete', 1, u'2011-03-01')],
                #         player1 won game3
                'win': {102: u'y'}
                })

        #
        # Show player1 games, complete, with wins from player1.
        #
        result = yield self.service.lobby({ 'in_progress': ['false'],
                                            'player_id': [player1],
                                            'my': ['true']})
        self.assertEquals(result, {
                #         player1 participated in game3 and was the author
                'games': [(102, u'SENTENCE3', u'complete', 1, u'2011-03-01')],
                #         player1 did not participate in game3
                #         player1 won game3
                'win': {102: u'y'}
                })

        #
        # Show player1 games, in progress, with wins from player1.
        #
        result = yield self.service.lobby({ 'in_progress': ['true'],
                                            'player_id': [player1],
                                            'my': ['true']})
        self.assertEquals(result, {
                #         player1 participates in game2 and was the author
                'games': [(101, u'SENTENCE2', u'invitation', 1, u'2011-05-01'),
                #         player1 was invited to game1
                          (100, u'SENTENCE1', u'invitation', 0, u'2011-02-01')],
                #         player1 won game3
                'win': {101: u'n'}
                })

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test10_"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesServiceTestInit))
    suite.addTest(loader.loadClass(CardstoriesServiceTest))
    suite.addTest(loader.loadClass(CardstoriesServiceTestHandle))
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
# compile-command: "python-coverage -e ; PYTHONPATH=.. python-coverage -x test_service.py ; python-coverage -m -a -r ../cardstories/service.py"
# End:
