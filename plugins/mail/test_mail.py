# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Loic Dachary <loic@dachary.org>
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Authors:
#          Loic Dachary <loic@dachary.org>
#          Adolfo R. Brandes <arbrandes@gmail.com>
#          Xavier Antoviaque <xavier@antoviaque.org>
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
from mock import Mock

from twisted.trial import unittest, runner, reporter
from twisted.internet import reactor, defer

from cardstories.service import CardstoriesService
from plugins.mail import mail

class Request:

    def __init__(self, **kwargs):
        self.args = kwargs

class MailTest(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)
        self.service = CardstoriesService({'db': self.database,
                                           'plugins-libdir': '../fixture',
                                           'plugins-confdir': '../fixture',
                                           'plugins-dir': '../fixture'})
        self.service.startService()

    def tearDown(self):
        return self.service.stopService()

    @defer.inlineCallbacks
    def complete_game(self):
        self.owner_id = 1
        self.player1 = 2
        self.player2 = 3
        self.owner_email = 'owner@example.com'
        self.player1_email = 'player1@example.com'
        self.player2_email = 'player2@example.com'
        self.winner_card = winner_card = 5
        sentence = 'SENTENCE'
        game = yield self.service.create({'owner_id': [self.owner_id]})
        self.game_id = game['game_id']
        yield self.service.set_card({ 'action': ['set_card'],
                                      'card': [winner_card],
                                      'game_id': [self.game_id],
                                      'player_id': [self.owner_id] })
        yield self.service.set_sentence({ 'action': ['set_sentence'],
                                          'sentence': [sentence],
                                          'game_id': [self.game_id],
                                          'player_id': [self.owner_id] })
        yield self.service.invite({ 'action': ['invite'],
                                    'game_id': [self.game_id],
                                    'invited_email': [self.player1_email],
                                    'owner_id': [self.owner_id] })
        for player_id in (self.player1, self.player2):
            yield self.service.participate({ 'action': ['participate'],
                                             'player_id': [player_id],
                                             'game_id': [self.game_id] })
            player = yield self.service.player2game({ 'action': ['player2game'],
                                                      'player_id': [player_id],
                                                      'game_id': [self.game_id] })
            card = player['cards'][0]
            yield self.service.pick({ 'action': ['pick'],
                                      'player_id': [player_id],
                                      'game_id': [self.game_id],
                                      'card': [card] })

        yield self.service.voting({ 'action': ['voting'],
                                    'game_id': [self.game_id],
                                    'owner_id': [self.owner_id] })
        winner_id = self.player1
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [self.game_id],
                                  'player_id': [winner_id],
                                  'card': [winner_card] })
        loser_id = self.player2
        yield self.service.vote({ 'action': ['vote'],
                                  'game_id': [self.game_id],
                                  'player_id': [loser_id],
                                  'card': [120] })
        self.assertTrue(self.service.games.has_key(self.game_id))
        yield self.service.complete({ 'action': ['complete'],
                                      'game_id': [self.game_id],
                                      'owner_id': [self.owner_id] })
        self.assertFalse(self.service.games.has_key(self.game_id))
        defer.returnValue(True)

    def test00_init(self):
        plugin = mail.Plugin(self.service, [ ])
        self.assertEquals(plugin.name(), 'mail')
        self.assertEquals(plugin.host, 'localhost')
        for allowed in mail.Plugin.ALLOWED:
            self.assertTrue(plugin.templates.has_key(allowed))

    @defer.inlineCallbacks
    def test01_invite(self):
        plugin = mail.Plugin(self.service, [ ])

        def get_player_email(player_id):
            if player_id == self.player1:
                email = self.player1_email
            elif player_id == self.player2:
                email = self.player2_email
            elif player_id == self.owner_id:
                email = self.owner_email
            return defer.succeed(email)
        self.service.auth.get_player_email = get_player_email

        def get_player_id(email, create=False):
            return defer.succeed(self.player1)
        self.service.auth.get_player_id = get_player_id

        self.count = 0

        def sendmail(host, sender, recipients, email):
            self.count += 1
            self.assertSubstring('game_id=%d' % self.game_id, email)
            self.assertSubstring('url=URL', email)
            self.assertSubstring('static_url=STATIC_URL', email)
            if self.count == 1:
                self.assertSubstring('_INVITE_', email)
                self.assertSubstring('owner_email=%s' % self.owner_name, email)
            elif self.count in (2, 3) :
                self.assertSubstring('_PICK_', email)
                if self.count == 2:
                    self.assertSubstring('player_email=%s' % self.player1_name, email)
                elif self.count == 3:
                    self.assertSubstring('player_email=%s' % self.player2_name, email)
            elif self.count in (4, 5) :
                self.assertSubstring('_VOTE_', email)
                if self.count == 4:
                    self.assertSubstring('player_email=%s' % self.player1_name, email)
                elif self.count == 5:
                    self.assertSubstring('player_email=%s' % self.player2_name, email)
            elif self.count == 6:
                self.assertSubstring('_VOTING_', email)
            elif self.count == 7:
                self.assertSubstring('_COMPLETE_', email)
                self.assertSubstring('owner_email=%s' % self.owner_name, email)
            return defer.succeed(True)
        plugin.sendmail = sendmail

        yield self.complete_game()
        self.assertEqual(self.count, 7)

    @defer.inlineCallbacks
    def test02_send_nothing(self):
        self.service.auth.get_players_emails = Mock(return_value=['not_an_email'])
        plugin = mail.Plugin(self.service, [ ])
        d = plugin.send('SUBJECT', [ 1 ], 'TEMPLATE', {})
        def check(result):
            self.assertFalse(result)
        d.addCallback(check)
        yield d


class MailTestAllow(unittest.TestCase):

    def setUp(self):
        self.database = 'test.sqlite'
        if os.path.exists(self.database):
            os.unlink(self.database)
        self.service = CardstoriesService({'db': self.database,
                                           'plugins-libdir': '../fixture2',
                                           'plugins-confdir': '../fixture2',
                                           'plugins-dir': '../fixture2'})
        self.service.startService()

    def tearDown(self):
        return self.service.stopService()

    def test00_init(self):
        plugin = mail.Plugin(self.service, [ ])
        for allowed in mail.Plugin.ALLOWED:
            has_key = plugin.templates.has_key(allowed)
            if allowed in ('invite', 'vote'):
                self.assertTrue(has_key)
            else:
                self.assertFalse(has_key)


def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(MailTest))
    suite.addTest(loader.loadClass(MailTestAllow))

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
# compile-command: "python-coverage -e ; PYTHONPATH=../.. python-coverage -x test_mail.py ; python-coverage -m -a -r mail.py"
# End:
