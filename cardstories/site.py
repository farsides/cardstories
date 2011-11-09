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
import json
from twisted.web import server, resource, static, http
from twisted.internet import defer
from twisted.python import urlpath, log

class CardstoriesSite(server.Site):
    
    def __init__(self, resource, settings, plugins, **kwargs):
        self.plugins = plugins
        name2plugin = {}
        for plugin in plugins:
            name2plugin[plugin.name()] = plugin
        self.preprocess = []
        for plugin in settings.get('plugins-pre-process', '').split():
            self.preprocess.append(name2plugin[plugin])
        self.postprocess = []
        for plugin in settings.get('plugins-post-process', '').split():
            self.postprocess.append(name2plugin[plugin])
        server.Site.__init__(self, resource, **kwargs)
    
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

        # pre-process the request ...
        for plugin in request.site.preprocess:
            d.addCallback(plugin.preprocess, request)
        # ... process the request ...
        d.addCallback(self.handle, request)
        # ... post-process the request.
        for plugin in request.site.postprocess:
            d.addCallback(plugin.postprocess)

        # catch errors and dump a trace ...
        def failed(reason):
            reason.printTraceback()
            if not request._disconnected:
                body = reason.getTraceback()
                request.setResponseCode(http.INTERNAL_SERVER_ERROR)
                request.setHeader('content-type',"text/html")
                request.setHeader('content-length', str(len(body)))
                request.write(body)
                request.finish()
            return True
        # ... or return the JSON result to the caller
        def succeed(result):
            if not request._disconnected:
                content = json.dumps(result)
                request.setHeader("content-length", str(len(content)))
                request.setHeader("content-type", 'application/json; charset="UTF-8"')
                request.setHeader("cache-control", 'no-cache');
                request.write(content)
                request.finish()
            return result
        d.addCallbacks(succeed, failed)

        return d

    def handle(self, result, request):
        return self.service.handle(result, request.args)

import os
import glob
import zipfile

class AGPLResource(static.File):

    def __init__(self, directory, module):
        self.directory = directory
        self.module = module
        self.zipfile = module.__name__ + '.zip'
        static.File.__init__(self, self.directory + '/' + self.zipfile)

    def render(self, request):
        self.update()
        return static.File.render(self, request)

    def update(self):
        directory = os.path.dirname(self.module.__file__)
        archive = self.directory + '/' + self.zipfile
        f = zipfile.ZipFile(archive, 'w')
        for path in glob.glob(directory + '/*.py'):
            f.write(path, os.path.basename(path))
        f.close()

class CardstoriesTree(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service
        self.putChild("resource", CardstoriesResource(self.service))
        self.putChild("static", static.File(service.settings['static']))
        import cardstories
        self.putChild("agpl", AGPLResource(service.settings['static'], cardstories))
        self.putChild("", self)

    def render_GET(self, request):
        return "Use /resource or /static or /agpl"
