#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Author: Adolfo R. Brandes <arbrandes@gmail.com>
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
from urllib import urlencode, urlopen
from simplejson import loads


class GraphAPI(object):
    """
    A client for the Facebook Graph API.  Given an OAuth access token, this
    will fetch the active user and his/her id:

       api = GraphAPI(access_token)
       user = api.get('me')
       id = user['id']

    Check the API reference for all available properties:
    http://developers.facebook.com/docs/reference/api/

    """
    def __init__(self, access_token=None):
        self.access_token = access_token

    def get(self, id):
        params = {'access_token': self.access_token}
        url = 'https://graph.facebook.com/%s?%s' % (id, urlencode(params))
        data = urlopen(url).read()
        response = loads(data)
        if response.get('error'):
            raise GraphAPIError(response['error'].get('code', 1),
                                response['error']['message'])

        return response

class GraphAPIError(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code
