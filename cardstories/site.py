#
# Copyright (C) 2011 Dachary <loic@dachary.org>
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
import json
from twisted.web import server, resource, static, http
from twisted.internet import defer

class CardstoriesResource(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.isLeaf = True

    def render(self, request):
        self.wrap_http(request)
        return server.NOT_DONE_YET

    def wrap_http(self, request):
        d = defer.succeed(True)
        
        def failed(reason):
            body = reason.getTraceback()
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            request.setHeader('content-type',"text/html")
            request.setHeader('content-length', str(len(body)))
            request.write(body)
            request.finish()

        def succeed(result):
            content = json.dumps(result)
            request.setHeader("content-length", str(len(content)))
            request.setHeader("content-type", 'application/json; charset="UTF-8"')
            request.write(content)
            request.finish()
            
        d.addCallback(self.handle, request)
        d.addCallbacks(succeed, failed)

        return d

    def handle(self, result, request):
        return self.service.handle(request.args)

class CardstoriesTree(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.putChild("resource", CardstoriesResource(self.service))
        self.putChild("static", static.File(service.settings['static']))
        self.putChild("", self)

    def render_GET(self, request):
        return "Use /resource or /static"
