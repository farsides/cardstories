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

from twisted.internet import defer


# Constants ###################################################################

NOT_IMPLEMENTED_ERROR_MSG = "A auth plugin must be loaded to implement this method"


# Exceptions ##################################################################

class AuthenticationError(Exception):
    """When the player_id/owner_id can't be authenticated'"""

    def __init__(self, requested_player_id, authenticated_player_id):
        self.requested_player_id = requested_player_id
        self.authenticated_player_id = authenticated_player_id

    def __str__(self):
        return "Requested player_id/owner_id = %s, but actually authenticated player_id = %s" \
                    % (self.requested_player_id, self.authenticated_player_id)


# Classes ####################################################################E

class Auth:
    '''Mock auth class
    
    Defines methods to be defined by an auth plugin
    To be registered as an auth plugin, a plugin must inherit from this class'''

    def authenticate(self, request, player_id):
        '''Check that the provided player_id is authorized for this request'''

        raise NotImplementedError(NOT_IMPLEMENTED_ERROR_MSG)

    def get_player_id(self, email, create=False):
        '''Returns the player_id corresponding to the provided email
        If create=True, create the player if it doesn't exist'''

        raise NotImplementedError(NOT_IMPLEMENTED_ERROR_MSG)

    def get_player_name(self, player_id):
        '''Returns the player name for a given player_id'''

        raise NotImplementedError(NOT_IMPLEMENTED_ERROR_MSG)

    def get_player_email(self, player_id):
        '''Returns the email corresponding to the provided player_id'''

        raise NotImplementedError(NOT_IMPLEMENTED_ERROR_MSG)

    @defer.inlineCallbacks
    def get_players_ids(self, emails, create=False):
        '''Returns a list of player_id corresponding to the provided list of emails
        If create=True, create the players if any doesn't exist'''
        
        ids = []
        for email in emails:
            if not isinstance(email, unicode):
                email = email.decode('utf-8')
                
            id = yield self.get_player_id(email, create=create)
            ids.append(id)
        defer.returnValue(ids)

    @defer.inlineCallbacks
    def get_players_emails(self, ids):
        '''Returns a list of emails, corresponding to the provided player_ids'''
        emails = []
        for id in ids:
            email = yield self.get_player_email(id)
            emails.append(email)
        defer.returnValue(emails)

    @defer.inlineCallbacks
    def get_players_names(self, ids):
        '''Returns a list of names, corresponding to the provided player_ids'''
        names = []
        for id in ids:
            name = yield self.get_player_name(id)
            names.append(name)
        defer.returnValue(names)

    @defer.inlineCallbacks
    def preprocess(self, result, request):
        for (key, values) in request.args.iteritems():
            if key == 'player_id' or key == 'owner_id':
                for player_id in values:
                    yield self.authenticate(request, player_id)
                
        defer.returnValue(result)

