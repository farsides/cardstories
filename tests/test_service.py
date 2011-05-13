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
from twisted.internet import defer, reactor
from twisted.web import server, resource, http

from cardstories.service import CardstoriesService

from twisted.internet import base
base.DelayedCall.debug = True

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
        player_id = 20
        db = sqlite3.connect(database)
        c = db.cursor()
        c.execute("INSERT INTO games (id) VALUES (%d)" % game_id)
        c.execute("INSERT INTO player2game (game_id, player_id) VALUES (%d, %d)" % ( game_id, player_id ))
        db.commit()
        db.close()

        service = CardstoriesService({'db': database})
        service.startService()
        self.assertEquals(game_id, service.games[game_id].id)
        self.assertEquals([player_id], service.games[game_id].get_players())
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
        return self.service.stopService()

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

    @defer.inlineCallbacks
    def test01_create(self):
        card = 5
        str_sentence = 'SENTENCE \xc3\xa9' # str containing unicode because that is what happens when
                                           # twisted web decodes %c3%a9
        utf8_sentence = u'SENTENCE \xe9'
        owner_id = 15
        result = yield self.service.create({ 'card': [card],
                                             'sentence': [str_sentence],
                                             'owner_id': [owner_id]})
        c = self.db.cursor()
        c.execute("SELECT * FROM games")
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        self.assertEquals(result['game_id'], rows[0][0])
        self.assertEquals(utf8_sentence, rows[0][3])
        self.assertEquals(chr(card), rows[0][5])
        self.assertEquals(self.service.games[result['game_id']].get_id(), result['game_id'])
        c.close()

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
        # route to the game function
        #
        class Game:
            def participate(self, args):
                self.participated = True
            def destroy(self):
                pass
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
        self.assertEquals(game_info['winner_card'], None)
        game_info = yield self.service.game({ 'game_id': [game['game_id']],
                                              'player_id': [owner_id] })
        self.assertEquals(game['game_id'], game_info['id'])
        self.assertEquals(game_info['winner_card'], winner_card)
        # if there is no in core representation of the game, 
        # a temporary one is created
        self.service.games[game_info['id']].destroy()
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
        self.db.commit()
        self.service.load(c)
        c.close()
        self.service.games[game1].modified = 111
        self.service.games[game2].modified = 222
        #
        # Show all games, in progress, with wins from player2.
        #
        result = yield self.service.lobby({ 'in_progress': ['true'],
                                            'player_id': [player2] })
        # game2 shows before game1 because it is created before
        self.assertEquals(result, {
                #         player2 does not participate in game2
                'games': [(game2, u'SENTENCE2', u'invitation', 0, u'2011-05-01'),
                #         player2 participates in game1 and is the author
                          (game1, u'SENTENCE1', u'invitation', 1, u'2011-02-01')],
                #         player2 did not yet win game1
                'win': {game1: u'n'},
                'modified': 0
                })

        #
        # Show player2 games, in progress, with wins from player2.
        #
        result = yield self.service.lobby({ 'in_progress': ['true'],
                                            'player_id': [player2],
                                            'my': ['true'] })
        self.assertEquals(result, {
                #         player2 participates in game1 and is the author
                'games': [(game1, u'SENTENCE1', u'invitation', 1, u'2011-02-01')],
                #         player2 does not participate in game2 therefore it is not shown
                #         player2 did not yet win game1
                'win': {game1: u'n'},
                'modified': self.service.games[game1].modified
                })

        #
        # Show all games, complete, with wins from player1.
        #
        result = yield self.service.lobby({ 'in_progress': ['false'],
                                            'player_id': [player1] })
        # game4 shows before game3 because it is created before
        self.assertEquals(result, {
                #         player1 did not participate in game3
                'games': [(game4, u'SENTENCE4', u'complete', 0, u'2011-06-01'),
                #         player1 participated in game3 and was the author
                          (game3, u'SENTENCE3', u'complete', 1, u'2011-03-01')],
                #         player1 won game3
                'win': {game3: u'y'},
                'modified': 0
                })

        #
        # Show player1 games, complete, with wins from player1.
        #
        result = yield self.service.lobby({ 'in_progress': ['false'],
                                            'player_id': [player1],
                                            'my': ['true']})
        self.assertEquals(result, {
                #         player1 participated in game3 and was the author
                'games': [(game3, u'SENTENCE3', u'complete', 1, u'2011-03-01')],
                #         player1 did not participate in game3
                #         player1 won game3
                'win': {game3: u'y'},
                #         player1 is in game2 and the modified field is 
                #         global to all games in progress, not just the ones 
                #         returned by the lobby request
                'modified': self.service.games[game2].modified
                })

        #
        # Show player1 games, in progress, with wins from player1.
        #
        result = yield self.service.lobby({ 'in_progress': ['true'],
                                            'player_id': [player1],
                                            'my': ['true']})
        self.assertEquals(result, {
                #         player1 participates in game2 and was the author
                'games': [(game2, u'SENTENCE2', u'invitation', 1, u'2011-05-01'),
                #         player1 was invited to game1
                          (game1, u'SENTENCE1', u'invitation', 0, u'2011-02-01')],
                #         player1 won game3
                'win': {game2: u'n'},
                'modified': self.service.games[game2].modified
                })

    def test06_get_or_create_player(self):
        # create a player that did not exist
        self.assertEquals({}, self.service.players)
        player_id = 1
        player = self.service.get_or_create_player(player_id)
        self.assertTrue(self.service.players.has_key(player_id))
        player.timer.cancel()
        # retrieve the same player
        self.assertEquals(player, self.service.get_or_create_player(player_id))
        # create a player and timeout too early : timer is rescheduled
        player_id = 2
        player = self.service.get_or_create_player(player_id)
        timer1 = player.timer
        func = player.timer.func
        func()
        self.assertNotEqual(timer1, player.timer)
        timer1.cancel()
        self.assertTrue(player.timer.active())
        # player timeout 
        def check(result):
            player.deleted = True
            self.assertTrue(result.has_key('delete'))
            return result
        d = player.poll({ 'modified': [player.modified + 100] })
        d.addCallback(check)
        player.access_time = 0 # pretend the player has not been accessed for a long time
        func = player.timer.func
        player.timer.cancel()
        self.assertTrue(func())
        self.assertTrue(player.deleted)
        self.assertFalse(self.service.players.has_key(player_id))
        # timeout on a deleted player does nothing
        self.assertFalse(func())

    @defer.inlineCallbacks
    def test07_game_notify(self):
        #
        # notify player called as a side effect of game.touch
        #
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        result = yield self.service.create({ 'card': [card],
                                             'sentence': [sentence],
                                             'owner_id': [owner_id]})
        game = self.service.games[result['game_id']]
        player = self.service.get_or_create_player(owner_id)
        player.modified -= 10
        before_modified = player.modified
        d = self.service.poll_player({ 'modified': [player.modified],
                                       'player_id': [owner_id] })
        def check(result):
            #
            # the modified time is from the player pollable, not
            # from the game pollable. 
            #
            self.assertTrue(result['modified'][0] > before_modified)
            self.assertEquals(result['modified'], [player.modified])
            self.assertEquals(result['player_id'], [owner_id])
            self.assertEquals(result['game_id'], [game.id])
            return result
        d.addCallback(check)
        game.touch() # calls game_notify indirectly
        #
        # calling game_notify on a non existent game is a noop
        #
        self.assertFalse(self.service.game_notify({}, 200))

    @defer.inlineCallbacks
    def test08_poll(self):
        #
        # missing argument raises exception
        #
        caught = False
        try:
            self.service.poll({'modified':[0]})
        except UserWarning, e:
            caught = True
            self.failUnlessSubstring('poll requires', e.args[0])
        self.assertTrue(caught)
        #
        # poll player
        #
        player_id = 10
        player = self.service.get_or_create_player(player_id)
        d = self.service.poll({'modified': [player.modified], 'player_id': [player_id]})
        def check(result):
            self.assertTrue(result['ok'])
            player.ok = True
            return result
        d.addCallback(check)
        player.touch({'ok': True})
        self.assertTrue(player.ok)
        #
        # poll game
        #
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        result = yield self.service.create({ 'card': [card],
                                             'sentence': [sentence],
                                             'owner_id': [owner_id]})
        game = self.service.games[result['game_id']]
        d = self.service.poll({'action': ['poll'],
                               'modified': [game.modified],
                               'game_id': [game.id]})
        def check(result):
            self.assertEquals([game.id], result['game_id'])
            game.ok = True
            return result
        d.addCallback(check)
        game.touch()
        self.assertTrue(game.ok)
        

    @defer.inlineCallbacks
    def test09_cancel(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'action': ['create'],
                                           'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        players = [ 16, 17 ]
        for player_id in players:
            yield self.service.participate({ 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [game['game_id']] })
        invited = 20
        yield self.service.invite({ 'action': ['invite'],
                                    'game_id': [game['game_id']],
                                    'player_id': [invited],
                                    'owner_id': [owner_id] })
        game = self.service.games[game['game_id']]
        self.assertEquals([owner_id] + players + [invited], game.get_players())
        yield game.cancel()
        self.assertFalse(self.service.games.has_key(game.id))

    @defer.inlineCallbacks
    def test10_invite(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'action': ['create'],
                                           'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        players = [ 16, 17 ]
        for player_id in players:
            yield self.service.participate({ 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [game['game_id']] })

        gameId = game['game_id']
        yield self.service.invite({ 'action': ['invite'],
                                    'game_id': [gameId],
                                    'owner_id': [owner_id] })
        game = self.service.games[game['game_id']]
        self.assertEquals([owner_id] + players, game.get_players())

        invited = 20
        yield self.service.invite({ 'action': ['invite'],
                                    'game_id': [gameId],
                                    'player_id': [invited],
                                    'owner_id': [owner_id] })
        game = self.service.games[gameId]
        self.assertEquals([owner_id] + players + [invited], game.get_players())

        yield game.cancel()
        self.assertFalse(self.service.games.has_key(game.id))

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test09_"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesServiceTestInit))
    suite.addTest(loader.loadClass(CardstoriesServiceTest))
    suite.addTest(loader.loadClass(CardstoriesServiceTestHandle))

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
