# -*- coding: utf-8 -*-
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

from mock import Mock

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer

from cardstories.service import CardstoriesService
from cardstories.poll import pollable

from twisted.internet import base
base.DelayedCall.debug = True

class CardstoriesServiceTestNotify(unittest.TestCase):
    
    def test00_notify(self):
        service = CardstoriesService({})
        d = service.listen()
        def check(result):
            self.assertTrue(result)
            service.checked = True
            return result
        d.addCallback(check)
        service.notify(True)
        self.assertTrue(service.checked)

    def test01_notify_recursive(self):
        service = CardstoriesService({})
        d = service.listen()
        def recurse(result):
            try:
                service.notify(False)
            except UserWarning, e:
                self.failUnlessSubstring('recurs', e.args[0])
                service.recursed = True
            return result
        d.addCallback(recurse)
        service.notify(True)
        self.assertTrue(service.recursed)

    def test02_notify_ignore_exception(self):
        service = CardstoriesService({})
        d = service.listen()
        def fail(result):
            service.raised = True
            raise UserWarning, 'raise exception'
        d.addCallback(fail)
        service.notify(True)
        self.assertTrue(service.raised)

class CardstoriesServiceTestInit(unittest.TestCase):

    def test00_startService(self):
        database = 'test.sqlite'
        service = CardstoriesService({'db': database})
        self.assertFalse(os.path.exists(database))
        def start(event):
            self.assertEqual(event['type'], 'start')
            service.notified_start = True
            return event
        service.listen().addCallback(start)
        service.startService()
        self.assertTrue(service.notified_start)
        self.assertTrue(os.path.exists(database))
        def stop(event):
            self.assertEqual(event['type'], 'stop')
            service.notified_stop = True
            return event
        service.listen().addCallback(stop)
        d = service.stopService()
        self.assertTrue(service.notified_stop)
        return d

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
        c.execute("INSERT INTO player2game (game_id, player_id) VALUES (%d, %d)" % (game_id, player_id))
        db.commit()
        db.close()

        service = CardstoriesService({'db': database})
        service.startService()
        self.assertEquals(game_id, service.games[game_id].id)
        self.assertEquals([player_id], service.games[game_id].get_players())
        self.assertEquals(len(service.games[game_id].pollers), 1)
        yield service.stopService()

class CardstoriesServiceTestBase(unittest.TestCase):

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

class CardstoriesServiceTestHandle(CardstoriesServiceTestBase):

    def test01_required(self):
        self.assertTrue(CardstoriesService.required({ 'key1': ['a'],
                                                      'key2': ['b'] }, 'method', 'key1'))
        
        self.failUnlessRaises(UserWarning, CardstoriesService.required, { }, 'method', 'key1')

    @defer.inlineCallbacks
    def test02_handle(self):
        for action in self.service.ACTIONS:
            result = yield self.service.handle(None, { 'action': [action] })
            self.failUnlessSubstring(action, result['error'])
            self.failUnlessSubstring('must be given', result['error'])

class CardstoriesServiceTest(CardstoriesServiceTestBase):

    @defer.inlineCallbacks
    def test01_create(self):
        card = 5
        str_sentence = 'SENTENCE \xc3\xa9' # str containing unicode because that is what happens when
                                           # twisted web decodes %c3%a9
        utf8_sentence = u'SENTENCE \xe9'
        owner_id = 15
        self.inited = False
        def accept(event):
            self.assertEquals(event['details']['type'], 'init')
            self.inited = True
        self.service.listen().addCallback(accept)
        result = yield self.service.create({ 'card': [card],
                                             'sentence': [str_sentence],
                                             'owner_id': [owner_id]})
        self.assertTrue(self.inited, 'init event called')
        c = self.db.cursor()
        c.execute("SELECT * FROM games")
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        self.assertEquals(result['game_id'], rows[0][0])
        self.assertEquals(utf8_sentence, rows[0][3])
        self.assertEquals(chr(card), rows[0][5])
        self.assertEquals(self.service.games[result['game_id']].get_id(), result['game_id'])
        c.close()

    def test02_game_method(self):
        game_id = 100
        for action in self.service.ACTIONS:
            getattr(self.service, action)
        #
        # checks if the game actually exists
        #
        caught = False
        try:
            self.service.game_method(game_id, 'participate', {'game_id': [game_id]})
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
        self.service.game_method(game_id, 'participate', {'game_id': [game_id] })
        self.assertTrue(self.service.games[game_id].participated)
        
    @defer.inlineCallbacks
    def test03_complete(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        for player_id in (16, 17):
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
        game_info, players_id_list = yield self.service.game({ 'game_id': [game['game_id']] })
        self.assertEquals(game['game_id'], game_info['id'])
        self.assertEquals(game_info['winner_card'], None)
        self.assertIn(owner_id, players_id_list)
        game_info, players_id_list = yield self.service.game({ 'game_id': [game['game_id']],
                                              'player_id': [owner_id] })
        self.assertEquals(game['game_id'], game_info['id'])
        self.assertEquals(game_info['winner_card'], winner_card)
        # if there is no in core representation of the game, 
        # a temporary one is created
        self.service.games[game_info['id']].destroy()
        game_info, players_id_list = yield self.service.game({ 'game_id': [game['game_id']] })
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
        c.execute("INSERT INTO games ( id, owner_id, sentence, state, created ) VALUES ( %d, %d, '%s', 'invitation', '2011-02-01' )" % (game1, player2, sentence1)) 
        c.execute("INSERT INTO invitations ( player_id, game_id ) VALUES ( %d, %d )" % (player1, game1))
        c.execute("INSERT INTO player2game ( player_id, game_id ) VALUES ( %d, %d )" % (player2, game1))

        c.execute("INSERT INTO games ( id, owner_id, sentence, state, created ) VALUES ( %d, %d, '%s', 'invitation', '2011-05-01' )" % (game2, player1, sentence2)) 
        c.execute("INSERT INTO player2game ( player_id, game_id, win ) VALUES ( %d, %d, 'n' )" % (player1, game2))
        # complete
        c.execute("INSERT INTO games ( id, owner_id, sentence, state, created ) VALUES ( %d, %d, '%s', 'complete', '2011-03-01' )" % (game3, player1, sentence3)) 
        c.execute("INSERT INTO player2game ( player_id, game_id, win ) VALUES ( %d, %d, 'y' )" % (player1, game3))

        c.execute("INSERT INTO games ( id, owner_id, sentence, state, created ) VALUES ( %d, %d, '%s', 'complete', '2011-06-01' )" % (game4, player2, sentence4)) 
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
        self.assertEquals(result, [{
                #         player2 does not participate in game2
                'games': [(game2, u'SENTENCE2', u'invitation', 0, u'2011-05-01'),
                #         player2 participates in game1 and is the author
                          (game1, u'SENTENCE1', u'invitation', 1, u'2011-02-01')],
                #         player2 did not yet win game1
                'win': {game1: u'n'},
                'modified': 0
                },
                [player2]])

        #
        # Show player2 games, in progress, with wins from player2.
        #
        result = yield self.service.lobby({ 'in_progress': ['true'],
                                            'player_id': [player2],
                                            'my': ['true'] })
        self.assertEquals(result, [{
                #         player2 participates in game1 and is the author
                'games': [(game1, u'SENTENCE1', u'invitation', 1, u'2011-02-01')],
                #         player2 does not participate in game2 therefore it is not shown
                #         player2 did not yet win game1
                'win': {game1: u'n'},
                'modified': self.service.games[game1].modified
                },
                [player2]])

        #
        # Show all games, complete, with wins from player1.
        #
        result = yield self.service.lobby({ 'in_progress': ['false'],
                                            'player_id': [player1] })
        # game4 shows before game3 because it is created before
        self.assertEquals(result, [{
                #         player1 did not participate in game3
                'games': [(game4, u'SENTENCE4', u'complete', 0, u'2011-06-01'),
                #         player1 participated in game3 and was the author
                          (game3, u'SENTENCE3', u'complete', 1, u'2011-03-01')],
                #         player1 won game3
                'win': {game3: u'y'},
                'modified': 0
                },
                [player1]])

        #
        # Show player1 games, complete, with wins from player1.
        #
        result = yield self.service.lobby({ 'in_progress': ['false'],
                                            'player_id': [player1],
                                            'my': ['true']})
        self.assertEquals(result, [{
                #         player1 participated in game3 and was the author
                'games': [(game3, u'SENTENCE3', u'complete', 1, u'2011-03-01')],
                #         player1 did not participate in game3
                #         player1 won game3
                'win': {game3: u'y'},
                #         player1 is in game2 and the modified field is 
                #         global to all games in progress, not just the ones 
                #         returned by the lobby request
                'modified': self.service.games[game2].modified
                },
                [player1]])

        #
        # Show player1 games, in progress, with wins from player1.
        #
        result = yield self.service.lobby({ 'in_progress': ['true'],
                                            'player_id': [player1],
                                            'my': ['true']})
        self.assertEquals(result, [{
                #         player1 participates in game2 and was the author
                'games': [(game2, u'SENTENCE2', u'invitation', 1, u'2011-05-01'),
                #         player1 was invited to game1
                          (game1, u'SENTENCE1', u'invitation', 0, u'2011-02-01')],
                #         player1 won game3
                'win': {game2: u'n'},
                'modified': self.service.games[game2].modified
                },
                [player1]])

    @defer.inlineCallbacks
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
        result = yield func()
        self.assertTrue(result)
        self.assertTrue(player.deleted)
        self.assertFalse(self.service.players.has_key(player_id))
        # timeout on a deleted player does nothing
        result = yield func()
        self.assertFalse(result)

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
            game.checked = True
            return result
        d.addCallback(check)
        def change(event):
            self.assertTrue(event['type'], 'change')
            self.assertTrue(event['game'].get_id(), game.get_id())
            game.changed = True
        self.service.listen().addCallback(change)
        yield game.touch() # calls game_notify indirectly
        self.assertTrue(game.checked)
        self.assertTrue(game.changed)
        #
        # Event notification when a game is destroyed
        #
        def destroy(event):
            self.assertTrue(event['type'], 'delete')
            self.assertTrue(event['game'].get_id(), game.get_id())
            game.destroyed = True
        self.service.listen().addCallback(destroy)            
        game.destroy()
        self.assertTrue(game.destroyed)
        #
        # calling game_notify on a non existent game is a noop
        #
        result = yield self.service.game_notify({}, 200)
        self.assertFalse(result)

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
            self.failUnlessSubstring('poll must be given', e.args[0])
        self.assertTrue(caught)
        #
        # poll player
        #
        player_id = 10
        player = self.service.get_or_create_player(player_id)
        d = self.service.poll({'action': ['poll'],
                               'type': ['lobby'],
                               'modified': [player.modified],
                               'player_id': [player_id]})
        def check(result):
            self.assertTrue(result['ok'])
            player.ok = True
            return result
        d.addCallback(check)
        yield player.touch({'ok': True})
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
                               'type': ['game'],
                               'modified': [game.modified],
                               'game_id': [game.id]})
        def check(result):
            self.assertEquals([game.id], result['game_id'])
            game.ok = True
            return result
        d.addCallback(check)
        yield game.touch()
        self.assertTrue(game.ok)
        #
        # poll plugins
        #
        class Plugin(pollable):
            def __init__(self):
                pollable.__init__(self, 200000000)
            def name(self):
                return 'plugin'
        plugin = Plugin()
        self.service.pollable_plugins.append(plugin)
        d = self.service.poll({'action': ['poll'],
                               'type': ['plugin'],
                               'modified': [plugin.get_modified()]})
        def check(result):
            self.assertEquals(['plugin'], result['type'])
            plugin.ok = True
            return result
        d.addCallback(check)
        yield plugin.touch({'type': ['plugin']})
        self.assertTrue(plugin.ok)

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
            
        invited = 'test@example.com'
        invited_id = 20
        # Fake call to auth module (id => name translation)
        def get_players_ids(emails, create):
            self.assertEquals(emails, [invited])
            self.assertEquals(create, True)
            return [invited_id]
        self.service.auth.get_players_ids = get_players_ids
        
        yield self.service.invite({ 'action': ['invite'],
                                    'game_id': [game['game_id']],
                                    'invited_email': [invited],
                                    'owner_id': [owner_id] })
        game = self.service.games[game['game_id']]
        self.assertEquals([owner_id] + players + [invited_id], game.get_players())
        yield game.cancel()
        self.assertFalse(self.service.games.has_key(game.id))

    @defer.inlineCallbacks
    def test10_invite(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        player_id = 18
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

        invited = 'test@example.com'
        invited_id = 20
        # Fake call to auth module (id => name translation)
        def get_players_ids(emails, create):
            self.assertEquals(emails, [invited])
            self.assertEquals(create, True)
            return [invited_id]
        self.service.auth.get_players_ids = get_players_ids
        yield self.service.invite({ 'action': ['invite'],
                                    'game_id': [gameId],
                                    'player_id': [player_id],
                                    'invited_email': [invited],
                                    'owner_id': [owner_id] })
        game = self.service.games[gameId]
        self.assertEquals([owner_id] + players + [invited_id, player_id], game.get_players())

        yield game.cancel()
        self.assertFalse(self.service.games.has_key(game.id))

    @defer.inlineCallbacks
    def test11_complete_and_poll(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        result = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})
        for player_id in (16, 17):
            yield self.service.participate({ 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [result['game_id']] })
            player = yield self.service.player2game({ 'action': ['player2game'],
                                                      'player_id': [player_id],
                                                      'game_id': [result['game_id']] })
            card = player['cards'][0]
            yield self.service.pick({ 'action': ['pick'],
                                      'player_id': [player_id],
                                      'game_id': [result['game_id']],
                                      'card': [card] })
        
        yield self.service.voting({ 'action': ['voting'],
                                    'game_id': [result['game_id']],
                                    'owner_id': [owner_id] })

        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % result['game_id'])
        board = c.fetchone()[0]
        winner_id = 16
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [result['game_id']],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = 17
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [result['game_id']],
                                  'player_id': [loser_id],
                                  'card': [120] })
        self.assertTrue(self.service.games.has_key(result['game_id']))
        game = self.service.games[result['game_id']]
        d = self.service.poll({'action': ['poll'],
                               'type': ['game'],
                               'modified': [game.modified],
                               'game_id': [game.id]})
        def check(result):
            self.assertEquals([game.id], result['game_id'])
            return result
        d.addCallback(check)
        yield self.service.complete({ 'action': ['complete'],
                                      'game_id': [result['game_id']],
                                      'owner_id': [owner_id] })
        self.assertFalse(self.service.games.has_key(result['game_id']))
        yield d

    @defer.inlineCallbacks
    def test12_player_info(self):
        player_id = 20
        player_name_format = u"pl\xe1y\u1ebdr %d"

        # Fake call to auth module (id => name translation)
        default_get_player_name = self.service.auth.get_player_name
        fake_get_player_name = Mock(return_value=player_name_format)
        self.service.auth.get_player_name = fake_get_player_name

        players_info = yield self.service.player_info({'type': 'player_info', 'player_id': [player_id]})
        fake_get_player_name.assert_called_once_with(player_id)
        
        self.assertEquals(players_info, [{'type': 'players_info', str(player_id): {'name': player_name_format}}])

        self.service.auth.get_player_name = default_get_player_name

    @defer.inlineCallbacks
    def test12_state(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        player_name_format = u"pl\xe1y\u1ebdr %d"

        # Fake call to auth module (id => name translation)
        def get_player_name(id):
            return player_name_format % id
        default_get_player_name = self.service.auth.get_player_name
        self.service.auth.get_player_name = get_player_name

        game = yield self.service.create({ 'card': [winner_card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})

        #
        # type = ['game']
        # 
        state = yield self.service.state({ 'type': ['game'],
                                           'modified': [0],
                                           'game_id': [game['game_id']] })
        self.assertEquals(game['game_id'], state[0]['id'])
        self.assertEquals(state[0]['winner_card'], None)
        state = yield self.service.state({ 'type': ['game'],
                                           'modified': [0],
                                           'game_id': [game['game_id']],
                                           'player_id': [owner_id] })
        self.assertEquals(game['game_id'], state[0]['id'])
        self.assertEquals(state[0]['winner_card'], winner_card)
        self.assertEquals(state[0]['type'], 'game')

        #
        # type = ['plugin']
        #
        class Plugin(pollable):
            def __init__(self):
                pollable.__init__(self, 200000000000)
            def state(self, args):
                return [{'info': True}, [owner_id]]
            def name(self):
                return 'plugin'
        plugin = Plugin()
        self.service.pollable_plugins.append(plugin)
        state = yield self.service.state({ 'type': ['plugin'],
                                           'modified': [0]})
        self.assertEquals(state[0]['type'], 'plugin')
        self.assertTrue(state[0]['info'])

        def check_players_info(state, players_info):
            # Check presence of players_info
            state_types_list = [x['type'] for x in state if 'type' in x]
            self.assertIn('players_info', state_types_list)

            # Check values of players_info
            state_players_info = [x for x in state if x['type'] == 'players_info']
            self.assertEquals(state_players_info, players_info)
        check_players_info(state, [{str(owner_id): {'name': player_name_format % owner_id}, 'type': 'players_info'}])

        #
        # type = ['lobby']
        #
        state = yield self.service.state({ 'type': ['lobby'],
                                           'modified': [0],
                                           'in_progress': ['true'],
                                           'player_id': [owner_id] })
        self.assertEquals(state[0]['type'], 'lobby')
        self.assertEquals(state[0]['games'][0][0], game['game_id'])
        check_players_info(state, [{str(owner_id): {'name': player_name_format % owner_id}, 'type': 'players_info'}])
        #
        # type = ['game','lobby','plugin']
        #
        state = yield self.service.state({ 'type': ['game', 'lobby', 'plugin'],
                                           'modified': [0],
                                           'game_id': [game['game_id']],
                                           'in_progress': ['true'],
                                           'player_id': [owner_id] })
        self.assertEquals(state[0]['type'], 'game')
        self.assertEquals(state[1]['type'], 'lobby')
        self.assertEquals(state[2]['type'], 'plugin')
        check_players_info(state, [{str(owner_id): {'name': player_name_format % owner_id}, 'type': 'players_info'}])

        self.service.auth.get_player_name = default_get_player_name

    @defer.inlineCallbacks
    def test13_set_countdown(self):
        card = 7
        sentence = 'SENTENCE'
        owner_id = 52
        game = yield self.service.create({ 'action': ['create'],
                                           'card': [card],
                                           'sentence': [sentence],
                                           'owner_id': [owner_id]})

        gameId = game['game_id']
        yield self.service.set_countdown({ 'action': ['set_countdown'],
                                           'duration': ['3600'],
                                           'game_id': [game['game_id']] })

        game = self.service.games[game['game_id']]
        self.assertEquals(3600, game.get_countdown_duration())

    @defer.inlineCallbacks
    def test14_poll_destroyed_game(self):
        game = yield self.service.create({ 'action': ['create'],
                                           'card': [12],
                                           'sentence': ['THE SENTENCE'],
                                           'owner_id': [22] })
        game_id = game['game_id']
        self.service.games[game_id].destroy()
        result = yield self.service.poll({ 'game_id': [game_id],
                                           'action': ['poll'],
                                           'type': ['game'],
                                           'modified': [1231] })
        self.assertTrue(type(result['modified'][0]) is long)


def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test12_"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesServiceTestNotify))
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
