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
import httplib2
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt

# An extremely simple HTTP proxy, meant for development only.
@csrf_exempt
def proxy(request, cardstories_host='localhost:5000'):
    try:
        get = "?%s" % request.GET.urlencode()
    except AttributeError:
        get = ''

    uri = r"http://%s%s%s" % (cardstories_host, request.path, get)
    connection = httplib2.Http()

    headers = {'Content-type': request.META['CONTENT_TYPE']}
    if 'HTTP_COOKIE' in request.META: # Don't break auth plugin
        headers['Cookie'] = request.META['HTTP_COOKIE']

    if request.method == 'GET':
        response, content = connection.request(uri, request.method,
                                               headers=headers)
    elif request.method == 'POST':
        body = request.raw_post_data
        response, content = connection.request(uri, request.method,
                                               headers=headers, body=body)

    status = int(response['status'])
    return HttpResponse(content, status=status,
                        mimetype=response['content-type'])
