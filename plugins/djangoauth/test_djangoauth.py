#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Authors:
#          Loic Dachary <loic@dachary.org>
#          Adolfo R. Brandes <arbrandes@gmail.com>
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

from plugins.djangoauth.djangoauth import Plugin


class FakeService:

    def __init__(self, settings):
        self.settings = settings


class DjangoAuthTest(unittest.TestCase):

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

        # Instantiate our test subject.
        self.djangoauth = Plugin(FakeService({'plugins-libdir': '.',
                                              'plugins-confdir': '../fixture'}), [])

        # Create a fake web client so that we don't need to set up an actual
        # web server to handle requests...
        class FakeClient:
            def getPage(self, url):
                from django.test.client import Client
                c = Client()
                u = urlparse(url)
                _url = u.path
                if u.query:
                    _url += "?" + u.query
                response = c.get(_url)
                return response._container[0]

        # ... and use it in the plugin instead of twisted's getPage.
        self.djangoauth.getPage = FakeClient().getPage


    def tearDown(self):
        from django.db import connection
        from django.test.utils import teardown_test_environment
        connection.creation.destroy_test_db(self.django_db, verbosity=0)
        teardown_test_environment()

    def test00_init(self):
        self.assertEqual(self.djangoauth.name(), "djangoauth")

    @defer.inlineCallbacks
    def test01_translate(self):
        rand = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for i in xrange(10))
        owner = u'%s@email.com' % rand
        player = u'player@email.com'
        invited = u'invited@email.com'

        # First, create the owner and log him in so that we can get a sessionid
        # from the cookie.
        from django.test.client import Client
        c = Client()
        url = "/register/"
        data = {'name': rand,
                'username': owner,
                'password1': rand,
                'password2': rand}
        c.post(url, data)
        sessionid = c.cookies["sessionid"].value

        class request:
            def __init__(self):
                self.args = {'action': ['invite'], 
                             'player_id': [ player, invited ],
                             'owner_id': [ owner ]}

            def getCookie(self, key):
                return sessionid

        request1 = request()
        result_in = 'RESULT'
        result_out = yield self.djangoauth.preprocess(result_in, request1)
        self.assertEquals(result_in, result_out)
        self.assertEquals(int, type(request1.args['player_id'][0]))
        self.assertEquals(int, type(request1.args['player_id'][1]))
        self.assertEquals(int, type(request1.args['owner_id'][0]))
        self.assertNotEquals(request1.args['player_id'], request1.args['owner_id'])
        request2 = request()
        result_in = 'RESULT'
        result_out = yield self.djangoauth.preprocess(result_in, request2)
        self.assertEquals(request1.args['player_id'][0], request2.args['player_id'][0])
        self.assertEquals(request1.args['player_id'][1], request2.args['player_id'][1])
        self.assertEquals(request1.args['owner_id'][0], request2.args['owner_id'][0])

        result_in = [{ 'players': [ [ request1.args['player_id'][0] ],
                                   [ request1.args['owner_id'][0] ]
                                   ],
                      'invited': [ request1.args['player_id'][0] ] }]
        result_out = yield self.djangoauth.postprocess(result_in)
        self.assertEquals(result_out, [{ 'players': [ [ player ],
                                                     [ owner ] ],
                                        'invited': [ player ]}])


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
