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
import re
sys.path.insert(0, os.path.abspath("..")) # so that for M-x pdb works
import sqlite3

from mock import Mock

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer
import twisted.web.error

from cardstories.service import CardstoriesService, CardstoriesServiceConnector
from cardstories.poll import Pollable
from cardstories.exceptions import CardstoriesWarning, CardstoriesException

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
        service.notify({'type': 'test'})
        self.assertTrue(service.checked)

    def test01_notify_recursive(self):
        service = CardstoriesService({})
        d = service.listen()
        def recurse(result):
            try:
                service.notify({'type': 'test-lock-fail'})
            except CardstoriesException, e:
                self.failUnlessSubstring('test-lock-fail', e.args[0])
                service.recursed = True
            return result
        d.addCallback(recurse)
        service.notify({'type': 'test-lock-fail'})
        self.assertTrue(service.recursed)

    def test02_notify_ignore_exception(self):
        service = CardstoriesService({})
        d = service.listen()
        def fail(result):
            service.raised = True
            raise CardstoriesException, 'raise exception'
        d.addCallback(fail)
        service.notify({'type': 'test'})
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

        self.failUnlessRaises(CardstoriesException, CardstoriesService.required, { }, 'method', 'key1')

    @defer.inlineCallbacks
    def test02_handle(self):
        # Make sure log.err() is called, but don't let it fail the tests
        from cardstories import service
        orig_service_log = service.log
        service.log = Mock()

        for action in self.service.ACTIONS:
            result = yield self.service.handle(None, { 'action': [action] })
            self.assertEquals('PANIC', result['error']['code'])
            self.failUnlessSubstring(action, result['error']['data'])
            self.failUnlessSubstring('requires argument', result['error']['data'])
            self.assertEqual(service.log.err.call_count, 1)
            service.log.reset_mock()

        service.log = orig_service_log

class CardstoriesServiceTest(CardstoriesServiceTestBase):

    @defer.inlineCallbacks
    def test01_create(self):
        owner_id = 15
        card = 5
        str_sentence = 'SENTENCE \xc3\xa9' # str containing unicode because that is what happens when
                                           # twisted web decodes %c3%a9
        utf8_sentence = u'SENTENCE \xe9'

        self.create_touch = False
        def accept(event):
            self.assertEquals(event['details']['type'], 'create')
            self.assertEquals(event['details']['previous_game_id'], None)
            self.create_touch = True
        self.service.listen().addCallback(accept)
        result = yield self.service.create({'owner_id': [owner_id]})
        self.assertTrue(self.create_touch, 'create event called')

        game_id = result['game_id']

        self.set_card_touch = False
        def accept(event):
            self.assertEquals(event['details']['type'], 'set_card')
            self.set_card_touch = True
        self.service.listen().addCallback(accept)
        result = yield self.service.set_card({'action': ['set_card'],
                                              'card': [card],
                                              'game_id': [game_id],
                                              'player_id': [owner_id]})
        self.assertTrue(self.set_card_touch, 'set_card event called')

        self.set_sentence_touch = False
        def accept(event):
            self.assertEquals(event['details']['type'], 'set_sentence')
            self.set_sentence_touch = True
        self.service.listen().addCallback(accept)
        result = yield self.service.set_sentence({'action': ['set_sentence'],
                                                  'sentence': [str_sentence],
                                                  'game_id': [game_id],
                                                  'player_id': [owner_id]})
        self.assertTrue(self.set_card_touch, 'set_sentence event called')

        c = self.db.cursor()
        c.execute("SELECT * FROM games")
        rows = c.fetchall()
        self.assertEquals(1, len(rows))
        self.assertEquals(game_id, rows[0][0])
        self.assertEquals(utf8_sentence, rows[0][3])
        self.assertEquals(chr(card), rows[0][5])
        self.assertEquals(self.service.games[game_id].get_id(), game_id)
        c.close()

    @defer.inlineCallbacks
    def test01_create_notify_previous_game_id(self):
        owner_id = 15
        self.inited = False
        previous_game_id = 30
        def accept(event):
            self.assertEquals(event['details']['type'], 'create')
            self.assertEquals(event['details']['previous_game_id'], previous_game_id)
            self.inited = True
        self.service.listen().addCallback(accept)
        result = yield self.service.create({'owner_id': [owner_id],
                                            'previous_game_id': [previous_game_id]})
        self.assertTrue(self.inited, 'init event called')

    @defer.inlineCallbacks
    def test01_load_notify(self):
        card = 5
        str_sentence = 'SENTENCE'
        owner_id = 15
        self.loaded = False
        result = yield self.service.create({'owner_id': [owner_id]})

        service2 = CardstoriesService({'db': self.database})

        def accept(event):
            self.assertEquals(event['details']['type'], 'load')
            self.loaded = True
        service2.listen().addCallback(accept)

        service2.startService()
        service2.stopService()
        self.assertTrue(self.loaded, 'load event called')

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
        except CardstoriesWarning, e:
            caught = True
            self.assertEquals('GAME_NOT_LOADED', e.code)
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
        game = yield self.service.create({'owner_id': [owner_id]})
        game_id = game['game_id']

        yield self.service.set_card({'action': ['set_card'],
                                     'card': [winner_card],
                                     'game_id': [game_id],
                                     'player_id': [owner_id]})
        yield self.service.set_sentence({'action': ['set_sentence'],
                                         'sentence': [sentence],
                                         'game_id': [game_id],
                                         'player_id': [owner_id]})

        for player_id in (16, 17):
            yield self.service.participate({ 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [game_id] })
            player = yield self.service.player2game({ 'action': ['player2game'],
                                                      'player_id': [player_id],
                                                      'game_id': [game_id] })
            card = player['cards'][0]
            yield self.service.pick({ 'action': ['pick'],
                                      'player_id': [player_id],
                                      'game_id': [game_id],
                                      'card': [card] })

        yield self.service.voting({ 'action': ['voting'],
                                    'game_id': [game_id],
                                    'owner_id': [owner_id] })

        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % game_id)
        board = c.fetchone()[0]
        winner_id = 16
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [game_id],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = 17
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [game_id],
                                  'player_id': [loser_id],
                                  'card': [120] })
        self.assertTrue(self.service.games.has_key(game_id))
        yield self.service.complete({ 'action': ['complete'],
                                      'game_id': [game_id],
                                      'owner_id': [owner_id] })
        self.assertFalse(self.service.games.has_key(game_id))

    @defer.inlineCallbacks
    def test04_game(self):
        winner_card = 5
        owner_id = 15
        game = yield self.service.create({'owner_id': [owner_id]})
        game_id = game['game_id']
        yield self.service.set_card({'action': ['set_card'],
                                     'card': [winner_card],
                                     'game_id': [game_id],
                                     'player_id': [owner_id]})
        game_info, players_id_list = yield self.service.game({'action': 'game',
                                                              'game_id': [game_id]})
        self.assertEquals(game_id, game_info['id'])
        self.assertEquals(game_info['winner_card'], None)
        self.assertIn(owner_id, players_id_list)
        game_info, players_id_list = yield self.service.game({ 'action': 'game',
                                                               'game_id': [game_id],
                                                               'player_id': [owner_id] })
        self.assertEquals(game_id, game_info['id'])
        self.assertEquals(game_info['winner_card'], winner_card)
        # if there is no in core representation of the game,
        # a temporary one is created
        self.service.games[game_info['id']].destroy()
        game_info, players_id_list = yield self.service.game({ 'action': 'game',
                                                               'game_id': [game_id] })
        self.assertEquals(game_id, game_info['id'])

    @defer.inlineCallbacks
    def test07_game_notify(self):
        #
        # notify player called as a side effect of game.touch
        #
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        result = yield self.service.create({'owner_id': [owner_id]})
        game = self.service.games[result['game_id']]

        def change(event):
            self.assertTrue(event['type'], 'change')
            self.assertTrue(event['game'].get_id(), game.get_id())
            game.changed = True
        self.service.listen().addCallback(change)
        yield game.touch() # calls game_notify indirectly
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
        except CardstoriesException, e:
            caught = True
            self.failUnlessSubstring("Action 'poll' requires argument", e.args[0])
        self.assertTrue(caught)

        #
        # poll game
        #
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        result = yield self.service.create({'owner_id': [owner_id]})
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
        class Plugin(Pollable):
            def __init__(self):
                Pollable.__init__(self, 200000000)
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
    def test08_poll_tabs(self):
        card = 7
        sentence = 'SENTENCE'
        owner_id = 17
        # Create three games and associate them with the owner in the tabs table.
        game_ids = []
        for i in range(3):
            result = yield self.service.create({'owner_id': [owner_id]})
            game_id = result['game_id']
            game_ids.append(game_id)

        # Stub out the get_tab_game_ids to return the tree games created above.
        def fake_get_tab_game_ids(args):
            d = defer.Deferred()
            d.callback(game_ids)
            return d
        self.service.get_tab_game_ids = fake_get_tab_game_ids

        games = map(lambda gid: self.service.games[gid], game_ids)
        max_modified = games[2].modified

        # Will be triggered when the test has finished.
        test_finish = defer.Deferred()

        # Touch first game.
        d = self.service.poll({'action': ['poll'],
                               'type': ['tabs'],
                               'modified': [max_modified],
                               'player_id': [owner_id],
                               'game_id': [game_ids[0]]})

        def check1(result):
            self.assertEquals(games[0].modified, result['modified'][0])
            games[0].ok = True
            return result

        d.addCallback(check1)
        games[0].touch()
        self.assertTrue(games[0].ok)

        # Touch third game.
        max_modified = games[0].modified # first game has just been touched, so it's the last one modified.
        ready = defer.Deferred()
        d = self.service.poll({'action': ['poll'],
                               'type': ['tabs'],
                               'modified': [max_modified],
                               'player_id': [owner_id],
                               'game_id': [game_ids[2]]})

        def check3(result):
            self.assertEquals(games[2].modified, result['modified'][0])
            games[2].ok = True
            return result
        d.addCallback(check3)
        yield games[2].touch()
        self.assertTrue(games[2].ok)


    @defer.inlineCallbacks
    def test09_cancel(self):
        card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        game = yield self.service.create({'owner_id': [owner_id]})
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
        game = yield self.service.create({'owner_id': [owner_id]})
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
        game = yield self.service.create({'owner_id': [owner_id]})
        game_id = game['game_id']
        yield self.service.set_card({'action': ['set_card'],
                                     'card': [winner_card],
                                     'game_id': [game_id],
                                     'player_id': [owner_id]})
        yield self.service.set_sentence({'action': ['set_sentence'],
                                         'sentence': [sentence],
                                         'game_id': [game_id],
                                         'player_id': [owner_id]})

        for player_id in (16, 17):
            yield self.service.participate({ 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [game_id] })
            player = yield self.service.player2game({ 'action': ['player2game'],
                                                      'player_id': [player_id],
                                                      'game_id': [game_id] })
            card = player['cards'][0]
            yield self.service.pick({ 'action': ['pick'],
                                      'player_id': [player_id],
                                      'game_id': [game_id],
                                      'card': [card] })

        yield self.service.voting({ 'action': ['voting'],
                                    'game_id': [game_id],
                                    'owner_id': [owner_id] })

        c = self.db.cursor()
        c.execute("SELECT board FROM games WHERE id = %d" % game_id)
        board = c.fetchone()[0]
        winner_id = 16
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [game_id],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = 17
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [game_id],
                                  'player_id': [loser_id],
                                  'card': [120] })
        self.assertTrue(self.service.games.has_key(game_id))
        game = self.service.games[game_id]
        d = self.service.poll({'action': ['poll'],
                               'type': ['game'],
                               'modified': [game.modified],
                               'game_id': [game.id]})
        def check(result):
            self.assertEquals([game.id], result['game_id'])
            return result
        d.addCallback(check)
        yield self.service.complete({ 'action': ['complete'],
                                      'game_id': [game_id],
                                      'owner_id': [owner_id] })
        self.assertFalse(self.service.games.has_key(game_id))
        yield d

    @defer.inlineCallbacks
    def test12_player_info(self):
        player_id = 20
        player_name = u"pl\xe1y\u1ebdr"
        player_avatar_url = "http://example.com/test.jpg"

        # Fake calls to auth module
        default_get_player_name = self.service.auth.get_player_name
        fake_get_player_name = Mock(return_value=player_name)
        self.service.auth.get_player_name = fake_get_player_name

        default_get_player_avatar_url = self.service.auth.get_player_avatar_url
        fake_get_player_avatar_url = Mock(return_value=player_avatar_url)
        self.service.auth.get_player_avatar_url = fake_get_player_avatar_url

        players_info = yield self.service.player_info({'type': 'player_info', 'player_id': [player_id]})
        fake_get_player_name.assert_called_once_with(player_id)
        fake_get_player_avatar_url.assert_called_once_with(player_id)

        self.assertEquals(players_info, [{ 'type': 'players_info',
                                           str(player_id): {'name': player_name,
                                                            'avatar_url': player_avatar_url}
                                         }])

        self.service.auth.get_player_name = default_get_player_name
        self.service.auth.get_player_avatar_url = default_get_player_avatar_url

    @defer.inlineCallbacks
    def test12_remove_tab(self):
        player_id = 21
        game_id1 = 121
        game_id2 = 122
        # Associate two games with the player in the tabs table.
        sql = "INSERT INTO tabs (player_id, game_id, created) VALUES (%d, %d, datetime('now'))"
        c = self.db.cursor()
        c.execute(sql % (player_id, game_id1))
        c.execute(sql % (player_id, game_id2))
        self.db.commit()

        # Helper function to get player's tabs from the DB.
        def get_player_tabs():
            c = self.db.cursor()
            c.execute("SELECT game_id FROM tabs WHERE player_id = ?", [player_id])
            game_ids = c.fetchall()
            return game_ids

        self.assertEqual(len(get_player_tabs()), 2)

        yield self.service.remove_tab({'action': ['remove_tab'],
                                       'player_id': [player_id],
                                       'game_id': [game_id1]})

        game_ids = get_player_tabs()
        self.assertEqual(len(game_ids), 1)
        self.assertEqual(game_ids[0][0], game_id2)

        # Trying to delete the same game again shouldn't do any harm.
        yield self.service.remove_tab({'action': ['remove_tab'],
                                       'player_id': [player_id],
                                       'game_id': [game_id1]})

        game_ids = get_player_tabs()
        self.assertEqual(len(game_ids), 1)
        self.assertEqual(game_ids[0][0], game_id2)

        # Delete the second game, too.
        # Trying to delete the same game again shouldn't do any harm.
        yield self.service.remove_tab({'action': ['remove_tab'],
                                       'player_id': [player_id],
                                       'game_id': [game_id2]})

        self.assertEqual(len(get_player_tabs()), 0)

    @defer.inlineCallbacks
    def test12_state(self):
        winner_card = 5
        sentence = 'SENTENCE'
        owner_id = 15
        player_name = u"pl\xe1y\u1ebdr"
        player_avatar_url = "http://example.com/test.jpg"

        players_info = [{'type': 'players_info', str(owner_id): {'name': player_name,
                                                                 'avatar_url': player_avatar_url}}]

        # Fake calls to auth module
        default_get_player_name = self.service.auth.get_player_name
        fake_get_player_name = Mock(return_value=player_name)
        self.service.auth.get_player_name = fake_get_player_name

        default_get_player_avatar_url = self.service.auth.get_player_avatar_url
        fake_get_player_avatar_url = Mock(return_value=player_avatar_url)
        self.service.auth.get_player_avatar_url = fake_get_player_avatar_url

        game = yield self.service.create({'owner_id': [owner_id]})
        game_id = game['game_id']

        yield self.service.set_card({'action': ['set_card'],
                                     'card': [winner_card],
                                     'game_id': [game_id],
                                     'player_id': [owner_id]})
        yield self.service.set_sentence({'action': ['set_sentence'],
                                         'sentence': [sentence],
                                         'game_id': [game_id],
                                         'player_id': [owner_id]})

        #
        # type = ['game']
        #
        state = yield self.service.state({ 'type': ['game'],
                                           'modified': [0],
                                           'game_id': [game_id] })
        self.assertEquals(game_id, state[0]['id'])
        self.assertEquals(state[0]['winner_card'], None)
        state = yield self.service.state({ 'type': ['game'],
                                           'modified': [0],
                                           'game_id': [game_id],
                                           'player_id': [owner_id] })
        self.assertEquals(game_id, state[0]['id'])
        self.assertEquals(state[0]['winner_card'], winner_card)
        self.assertEquals(state[0]['type'], 'game')

        #
        # type = ['tabs']
        #
        # Create two games.
        winner_card1 = 18
        winner_card2 = 19
        sentence1 = 'SENTENCE1'
        sentence2 = 'SENTENCE2'
        player_id = 100
        owner_id1 = 101

        game1 = yield self.service.create({'owner_id': [owner_id1]})
        game_id1 = game1['game_id']
        yield self.service.set_card({'action': ['set_card'],
                                     'card': [winner_card1],
                                     'game_id': [game_id1],
                                     'player_id': [owner_id1]})
        yield self.service.set_sentence({'action': ['set_sentence'],
                                         'sentence': [sentence1],
                                         'game_id': [game_id1],
                                         'player_id': [owner_id1]})

        game2 = yield self.service.create({'owner_id': [player_id]})
        game_id2 = game2['game_id']
        yield self.service.set_card({'action': ['set_card'],
                                     'card': [winner_card2],
                                     'game_id': [game_id2],
                                     'player_id': [player_id]})
        yield self.service.set_sentence({'action': ['set_sentence'],
                                         'sentence': [sentence2],
                                         'game_id': [game_id2],
                                         'player_id': [player_id]})

        # Associate the first game with the player, and pass the ID of
        # the second one as 'game_id' to the state call - the state function
        # should automatically associate the second game with player's tabs,
        # and return states of both.
        sql = "INSERT INTO tabs (player_id, game_id, created) VALUES (%d, %d, datetime('now'))"
        c = self.db.cursor()
        c.execute(sql % (player_id, game_id1))
        self.db.commit()

        modified1 = self.service.games[game_id1].modified
        modified2 = self.service.games[game_id2].modified
        max_modified = max(modified1, modified2)
        multistate = yield self.service.state({'type': ['tabs'],
                                               'modified': [0],
                                               'game_id': [game_id2],
                                               'player_id': [player_id]})

        self.assertEquals(multistate[0]['modified'], max_modified)
        self.assertEquals(len(multistate[0]['games']), 2)
        state1 = multistate[0]['games'][0]
        self.assertEquals(state1['id'], game_id1)
        self.assertEquals(state1['winner_card'], None)
        state2 = multistate[0]['games'][1]
        self.assertEquals(state2['id'], game_id2)
        self.assertEquals(state2['winner_card'], winner_card2)
        # Look into the database to assert that the second game has been associated
        # with the player in the 'tabs' table.
        c = self.db.cursor()
        c.execute('SELECT game_id from tabs where player_id = ? ORDER BY created ASC', [player_id])
        games = c.fetchall()
        self.assertEquals(len(games), 2)
        self.assertEquals(games[0][0], game_id1)
        self.assertEquals(games[1][0], game_id2)

        #
        # type = ['plugin']
        #
        class Plugin(Pollable):
            def __init__(self):
                Pollable.__init__(self, 200000000000)
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

        def check_players_info(state):
            # Check presence of players_info
            state_types_list = [x['type'] for x in state if 'type' in x]
            self.assertIn('players_info', state_types_list)

            # Check values of players_info
            state_players_info = [x for x in state if x['type'] == 'players_info']
            self.assertEquals(state_players_info, players_info)
        check_players_info(state)

        #
        # type = ['game','tabs','plugin']
        #
        state = yield self.service.state({ 'type': ['game', 'tabs', 'plugin'],
                                           'modified': [0],
                                           'game_id': [game_id],
                                           'player_id': [owner_id] })
        self.assertEquals(state[0]['type'], 'game')
        self.assertEquals(state[1]['type'], 'tabs')
        self.assertEquals(state[2]['type'], 'plugin')
        check_players_info(state)

        self.service.auth.get_player_name = default_get_player_name
        self.service.auth.get_player_avatar_url = default_get_player_avatar_url

    @defer.inlineCallbacks
    def test12_player_info_on_error(self):
        player_id = 12

        # Fake calls to auth module
        default_get_player_name = self.service.auth.get_player_name
        def fake_get_player_name(self):
            raise twisted.web.error.Error('404', 'NOT FOUND')
        self.service.auth.get_player_name = fake_get_player_name

        errmsg = None
        try:
            yield self.service.player_info({'type': 'player_info', 'player_id': [player_id]})
        except Exception as e:
            errmsg = e.message

        self.assertTrue(bool(re.match('Failed fetching player data \\(player_id=%d\\)' % player_id, errmsg)))

        self.service.auth.get_player_name = default_get_player_name

    @defer.inlineCallbacks
    def test13_set_countdown(self):
        card = 7
        sentence = 'SENTENCE'
        owner_id = 52
        result = yield self.service.create({'owner_id': [owner_id]})
        game_id = result['game_id']
        yield self.service.set_card({'action': ['set_card'],
                                     'card': [card],
                                     'game_id': [game_id],
                                     'player_id': [owner_id]})
        yield self.service.set_sentence({'action': ['set_sentence'],
                                         'sentence': [sentence],
                                         'game_id': [game_id],
                                         'player_id': [owner_id]})
        yield self.service.set_countdown({'action': ['set_countdown'],
                                          'duration': ['3600'],
                                          'game_id': [game_id]})

        game = self.service.games[game_id]
        self.assertEquals(3600, game.get_countdown_duration())

    @defer.inlineCallbacks
    def test14_poll_destroyed_game(self):
        game = yield self.service.create({'owner_id': [22] })
        game_id = game['game_id']
        self.service.games[game_id].destroy()
        result = yield self.service.poll({ 'game_id': [game_id],
                                           'action': ['poll'],
                                           'type': ['game'],
                                           'modified': [1231] })
        # Assert modified is numeric; concrete type depends on architecture/implementation.
        self.assertTrue(isinstance(result['modified'][0], (int, long)))

    def test15_poll_notification(self):
        args = { 'type': ['tabs'],
                 'action': ['poll'],
                 'player_id': [13],
                 'game_id': [20],
                 'modified': [10000000000000000] }

        # Fake poll controlled from the test
        poll = defer.Deferred()
        mock_poll_tabs = Mock()
        mock_poll_tabs.return_value = poll
        orig_service_poll_tabs = self.service.poll_tabs
        self.service.poll_tabs = mock_poll_tabs

        mock_listener = Mock()
        self.service.listen().addCallback(mock_listener)
        self.service.poll(args)
        mock_listener.assert_called_once_with({'player_id': 13, 'type': 'poll_start'})

        mock_listener.reset_mock()
        self.service.listen().addCallback(mock_listener)
        poll.callback(args)
        mock_listener.assert_called_once_with({'player_id': 13, 'type': 'poll_end'})

        self.service.poll_tabs = orig_service_poll_tabs

    @defer.inlineCallbacks
    def test16_set_card(self):
        card = 7
        owner_id = 52
        game = yield self.service.create({'owner_id': [owner_id]})
        game_id = game['game_id']

        yield self.service.set_card({'action': ['set_card'],
                                     'card': [card],
                                     'player_id': [owner_id],
                                     'game_id': [game_id] })

        state, player_id_list = yield self.service.games[game_id].game(owner_id)
        self.assertEquals(card, state['winner_card'])

    @defer.inlineCallbacks
    def test16_set_sentence(self):
        card = 8
        owner_id = 51
        sentence = 'THE SENTENCE'
        game = yield self.service.create({'owner_id': [owner_id]})
        game_id = game['game_id']

        yield self.service.set_card({'action': ['set_card'],
                                     'card': [card],
                                     'player_id': [owner_id],
                                     'game_id': [game_id] })
        yield self.service.set_sentence({'action': ['set_sentence'],
                                         'sentence': [sentence],
                                         'player_id': [owner_id],
                                         'game_id': [game_id] })

        state, player_id_list = yield self.service.games[game_id].game(owner_id)
        self.assertEquals(sentence, state['sentence'])

class CardstoriesConnectorTest(CardstoriesServiceTestBase):

    @defer.inlineCallbacks
    def create_game(self):
        # Fake auth module
        self.service.auth = Mock()

        self.card = 5
        self.sentence = u'SENTENCE'
        self.owner_id = 15
        result = yield self.service.create({'owner_id': [self.owner_id]})
        game_id = result['game_id']
        defer.returnValue(game_id)

    @defer.inlineCallbacks
    def test01_get_game_by_id(self):
        game_id = yield self.create_game()

        connector = CardstoriesServiceConnector(self.service)
        game, players_ids = yield connector.get_game_by_id(game_id, self.owner_id)
        self.assertEqual(game['id'], game_id)
        self.assertEqual(players_ids, [self.owner_id])

    @defer.inlineCallbacks
    def test02_get_players_by_game_id(self):
        game_id = yield self.create_game()

        connector = CardstoriesServiceConnector(self.service)
        players_ids = yield connector.get_players_by_game_id(game_id)
        self.assertEqual(players_ids, [self.owner_id])

    def test03_get_game_id_from_args(self):
        connector = CardstoriesServiceConnector(self.service)

        game_id = connector.get_game_id_from_args({})
        self.assertEqual(game_id, None)

        game_id = connector.get_game_id_from_args({'game_id': ['undefined']})
        self.assertEqual(game_id, None)

        game_id = connector.get_game_id_from_args({'game_id': ['3']})
        self.assertEqual(game_id, 3)

        game_id = connector.get_game_id_from_args({'game_id': [4]})
        self.assertEqual(game_id, 4)


def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test12_"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesServiceTestNotify))
    suite.addTest(loader.loadClass(CardstoriesServiceTestInit))
    suite.addTest(loader.loadClass(CardstoriesServiceTest))
    suite.addTest(loader.loadClass(CardstoriesServiceTestHandle))
    suite.addTest(loader.loadClass(CardstoriesConnectorTest))
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
