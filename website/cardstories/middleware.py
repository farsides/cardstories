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

from urllib import quote

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.core.urlresolvers import reverse

from views import welcome

class WelcomeCookieMiddleware(object):
    def __init__(self):
        # Only run when in development.
        if not settings.DEBUG:
            raise MiddlewareNotUsed

    def process_response(self, request, response):
        # Set welcome page URL for redirection, which will be needed for
        # logout, for example.
        if request.path == '/static/index.html':
            welcome_url = quote(reverse(welcome), '')
            response.set_cookie('CARDSTORIES_WELCOME', welcome_url)

        return response
