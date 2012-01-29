# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Authors:
#          Adolfo R. Brandes <arbrandes@gmail.com>
#          Xavier Antoviaque <xavier@antoviaque.org>
#          Matjaz Gregoric <mtyaka@gmail.com>
#          Loic Dachary <loic@dachary.org>
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
import random
sys.path.insert(0, os.path.abspath("../..")) # so that for M-x pdb works

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer

from urllib import urlencode
from urlparse import urlparse

from cardstories.auth import AuthenticationError
from plugins.djangoauth import djangoauth
from plugins.mail.test_mail import MailTest


class FakeTwistedWebClient:
    """
    A fake twisted.web.client that uses the django test framework, so that we
    don't need to set up an actual web server to handle requests.
    
    """
    def getPage(self, url):
        from django.test.client import Client
        c = Client()
        u = urlparse(url)
        _url = u.path
        if u.query:
            _url += "?" + u.query
        response = c.get(_url)
        return response._container[0]


class DjangoAuthTest(unittest.TestCase):
    """
    The django authentication test proper.
    
    """
    def setUp(self):
        # Set up the django test framework.
        os.environ['DJANGO_SETTINGS_MODULE'] = 'website.settings'
        from django.conf import settings
        from django.test.utils import setup_test_environment
        from django.db import connection

        # If DEBUG = True, django will sometimes take different code paths.
        settings.DEBUG = False

        self.django_db = settings.DATABASE_NAME
        setup_test_environment()
        connection.creation.create_test_db(verbosity=0)

        # A fake cardstories service just to benefit from settings directories.
        class FakeService:
            def __init__(self, settings):
                self.settings = settings

        # Instantiate our test subject.
        self.auth = djangoauth.Plugin(FakeService({'plugins-libdir': '.',
                                                   'plugins-confdir': '../fixture'}), [])

        # Use the fake client in the plugin instead of twisted's getPage.
        self.auth.getPage = FakeTwistedWebClient().getPage

    def tearDown(self):
        from django.db import connection
        from django.test.utils import teardown_test_environment
        connection.creation.destroy_test_db(self.django_db, verbosity=0)
        teardown_test_environment()

    def test00_init(self):
        self.assertEqual(self.auth.name(), "djangoauth")

    @defer.inlineCallbacks
    def test01_authenticate(self):
        owner_name = u'Game Owneré'
        rand = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for i in xrange(10))
        player_email = u'%s@email.com' % rand
        player_id = 1

        # First, create the owner and log him in so that we can get a sessionid
        # from the cookie.
        from django.test.client import Client
        c = Client()
        url = "/register/"
        data = {'name': owner_name,
                'username': player_email,
                'password1': rand,
                'password2': rand}
        c.post(url, data)
        sessionid = c.cookies["sessionid"].value

        class request:
            def __init__(self):
                self.sessionid = sessionid
            def getCookie(self, key):
                return self.sessionid

        # Successful authentication
        authorized_request = request()
        result = yield self.auth.authenticate(authorized_request, player_id)
        self.assertTrue(result)

        # Failed authentication
        unauthorized_request = request()
        unauthorized_request.sessionid = 'bad sessionid'
        error = False
        try:
            yield self.auth.authenticate(unauthorized_request, player_id)
        except AuthenticationError:
            error = True
        self.assertTrue(error)

    @defer.inlineCallbacks
    def test02_get_player_name(self):
        player_email = u'test02@foo.com'
        # For players that are created without the 'name' attribute,
        # the first part of the email (up to first '@' character) is
        # returned by django as the name.
        inferred_name = u'test02'
        (player_id,) = yield self.auth.get_players_ids((player_email,), create=True)
        resolved_player = yield self.auth.get_player_name(player_id)
        self.assertEquals(inferred_name, resolved_player)
        self.auth.getPage = None
        (resolved_player,) = yield self.auth.get_players_names((player_id,))
        self.assertEquals(inferred_name, resolved_player) # the second time around the cached answer is returned

    @defer.inlineCallbacks
    def test03_get_player_email(self):
        player_email = 'test03@foo.com'
        player_id = yield self.auth.get_player_id(player_email, create=True)
        resolved_email = yield self.auth.get_player_email(player_id)
        self.assertEquals(player_email, resolved_email)
        self.auth.getPage = None
        (resolved_email,) = yield self.auth.get_players_emails((player_id,))
        self.assertEquals(player_email, resolved_email) # the second time around the cached answer is returned


def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(DjangoAuthTest))

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
# compile-command: "python-coverage -e ; PYTHONPATH=../.. python-coverage -x test_djangoauth.py ; python-coverage -m -a -r djangoauth.py"
# End:
