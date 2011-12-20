# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Authors:
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

# Imports #####################################################################

import sys

from twisted.internet import defer
from twisted.trial import unittest, runner, reporter
from mock import Mock

from cardstories.auth import Auth
from cardstories.service import CardstoriesService

# Classes #####################################################################

class CardstoriesAuthTest(unittest.TestCase):
        
    @defer.inlineCallbacks
    def test00_request_auth(self):
        '''Check that the preprocess correctly calls the right plugin methods'''
        
        player_id = 10
        owner_id = 12
        sessionid = 'session_id_string'

        auth = Auth()
        auth.authenticate = Mock(return_value=True)
        
        # Should authenticate player_id parameters
        class request_player_id:
            def __init__(self):
                self.args = {'action': ['invite'],
                             'player_id': [player_id],
                             'invited_email': 'test@example.com'}
            def getCookie(self, key):
                return sessionid
            
        request = request_player_id()
        result_in = 'RESULT'
        result_out = yield auth.preprocess(result_in, request)
        self.assertEquals(result_in, result_out)
        auth.authenticate.assert_called_once_with(request, player_id)
        
        # And should authenticate owner_id parameters, too
        class request_owner_id:
            def __init__(self):
                self.args = {'action': ['invite'],
                             'owner_id': [owner_id]}
            def getCookie(self, key):
                return sessionid
            
        request = request_owner_id()
        result_in = 'RESULT'
        result_out = yield auth.preprocess(result_in, request)
        self.assertEquals(result_in, result_out)
        auth.authenticate.assert_called_with(request, owner_id)
        
    def test01_exception_if_no_auth_plugin(self):
        '''If auth no plugin is loaded, auth methods should raise NotImplemented'''
        
        service = CardstoriesService({})
        
        def check_not_implemented_method(method_name, *args, **kwargs):
            called = False
            try:
                method = getattr(service.auth, method_name)
                method(*args, **kwargs)
            except NotImplementedError:
                called = True
            self.assertEquals(called, True)
            
        check_not_implemented_method("authenticate", "request", "player_id")
        check_not_implemented_method("get_player_id", "email", create=True)
        check_not_implemented_method("get_player_name", "id")
        check_not_implemented_method("get_player_email", "id")
        check_not_implemented_method("get_player_avatar_url", "id")
        
    def test02_get_several_at_once(self):
        '''Generic methods to retreive several objects at once'''
        
        service = CardstoriesService({})
        
        def check_call_for_each(method_name_multiple, method_name_single):
            mock = Mock(return_value=0)
            setattr(service.auth, method_name_single, mock)
            method = getattr(service.auth, method_name_multiple)
            method(["1", "2", "3", "4"])
            self.assertEquals(mock.call_count, 4)
            
        check_call_for_each("get_players_ids", "get_player_id")
        check_call_for_each("get_players_names", "get_player_name")
        check_call_for_each("get_players_emails", "get_player_email")
        check_call_for_each("get_players_avatars_urls", "get_player_avatar_url")
        
            
# Main ########################################################################

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test12_"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesAuthTest))
    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
        
