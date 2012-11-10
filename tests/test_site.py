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
import sys
import os
sys.path.insert(0, os.path.abspath("..")) # so that for M-x pdb works

from twisted.trial import unittest, runner, reporter
from twisted.internet import defer
from twisted.web import server, resource
from twisted.python import filepath

from twisted.web.test.test_web import DummyRequest
from twisted.web.test._util import _render

from cardstories.site import CardstoriesResource, CardstoriesInternalResource
from cardstories.site import CardstoriesTree, AGPLResource, CardstoriesSite
from cardstories.plugins import CardstoriesPlugins

class CardstoriesServiceMockup:
    def __init__(self):
        self.settings = {'static': os.getcwd()}

    def handle(self, result, args, internal_request=False):
        return 'handle'

class CardstoriesSiteTest(unittest.TestCase):

    def test00_init(self):
        plugins = CardstoriesPlugins({ 'plugins-dir': '..',
                                       'plugins': 'plugin_one plugin_two'})
        class Service:
            def __init__(self):
                self.pollable_plugins = []
        service = Service()
        plugins.load(service)
        site = CardstoriesSite(resource.Resource(), { 'plugins-pre-process': 'plugin_one plugin_two',
                                                      'plugins-post-process': 'plugin_two plugin_one' }, plugins.plugins)
        self.assertEqual(site.preprocess[0], site.postprocess[1])
        self.assertEqual(site.preprocess[1], site.postprocess[0])

class CardstoriesResourceTest(unittest.TestCase):

    class Transport:
        host = None

        def getPeer(self):
            return None
        def getHost(self):
            return self.host

    class Channel:
        def __init__(self, site):
            self.transport = CardstoriesResourceTest.Transport()
            self.site = site

        def requestDone(self, request):
            pass

    def setUp(self):
        self.service = CardstoriesServiceMockup()

    def tearDown(self):
        if hasattr(self, 'site'):
            self.site.stopFactory()

    def test00_render(self):
        self.site = CardstoriesSite(CardstoriesTree(self.service), {}, [])
        r = server.Request(self.Channel(self.site), True)
        r.site = r.channel.site
        input = ''
        r.gotLength(len(input))
        r.handleContentChunk(input)
        r.queued = 0
        d = r.notifyFinish()
        def finish(result):
            self.assertSubstring('\r\n\r\n"handle"', r.transport.getvalue())
        d.addCallback(finish)
        r.requestReceived('GET', '/resource', '')
        return d

    def test00_render_static(self):
        file = "file"
        fd = open(file, "w")
        fd.write('CONTENT')
        fd.close()

        tree = CardstoriesTree(self.service)
        request = DummyRequest(['static', 'file'])
        child = resource.getChildForRequest(tree, request)

        self.assertTrue(isinstance(child, filepath.FilePath))
        d = _render(child, request)
        def finish(result):
            self.assertEquals(['CONTENT'], request.written)
        d.addCallback(finish)
        return d

    def test01_wrap_http(self):
        resource = CardstoriesResource(self.service)
        self.site = CardstoriesSite(resource, {}, [])
        request = server.Request(self.Channel(self.site), True)
        request.site = self.site
        request.method = 'GET'
        d = resource.wrap_http(request)
        def finish(result):
            self.assertSubstring('\r\n\r\n"handle"', request.transport.getvalue())
        d.addCallback(finish)
        return d

    def test01_wrap_http_disconnected(self):
        resource = CardstoriesResource(self.service)
        self.site = CardstoriesSite(resource, {}, [])
        request = server.Request(self.Channel(self.site), True)
        request.site = self.site
        request.method = 'GET'
        request._disconnected = True
        d = resource.wrap_http(request)
        def finish(result):
            self.assertEquals('', request.transport.getvalue())
        d.addCallback(finish)
        return d

    def test02_wrap_http_plugin(self):
        class MyService:
            def handle(self, result, args):
                return result

        plugins = CardstoriesPlugins({ 'plugins-dir': '..',
                                       'plugins': 'plugin_site'})
        plugins.load(True)
        resource = CardstoriesResource(MyService())
        self.site = CardstoriesSite(resource, { 'plugins-pre-process': 'plugin_site',
                                                'plugins-post-process': 'plugin_site' }, plugins.plugins)
        request = server.Request(self.Channel(self.site), True)
        request.site = self.site
        request.args = {}
        request.method = 'GET'
        d = resource.wrap_http(request)
        def finish(result):
            self.assertSubstring('"preprocess": ["PREPROCESS"]', request.transport.getvalue())
            self.assertSubstring('"postprocess": "POSTPROCESS"', request.transport.getvalue())
        d.addCallback(finish)
        return d

    def test02_wrap_http_plugin_preprocess_fail(self):
        plugins = CardstoriesPlugins({ 'plugins-dir': '..',
                                       'plugins': 'plugin_fail'})
        plugins.load(True)
        resource = CardstoriesResource(self.service)
        self.site = CardstoriesSite(resource, { 'plugins-pre-process': 'plugin_fail' }, plugins.plugins)
        request = server.Request(self.Channel(self.site), True)
        request.site = self.site
        request.method = 'GET'
        d = resource.wrap_http(request)
        def finish(result):
            self.assertSubstring('Internal Server Error', request.transport.getvalue())
            self.assertSubstring('PREPROCESS', request.transport.getvalue())
        d.addCallback(finish)
        return d

    def test02_wrap_http_plugin_postprocess_fail(self):
        plugins = CardstoriesPlugins({ 'plugins-dir': '..',
                                       'plugins': 'plugin_fail'})
        plugins.load(True)
        resource = CardstoriesResource(self.service)
        self.site = CardstoriesSite(resource, { 'plugins-post-process': 'plugin_fail' }, plugins.plugins)
        request = server.Request(self.Channel(self.site), True)
        request.site = self.site
        request.method = 'GET'
        d = resource.wrap_http(request)
        def finish(result):
            self.assertSubstring('Internal Server Error', request.transport.getvalue())
            self.assertSubstring('POSTPROCESS', request.transport.getvalue())
        d.addCallback(finish)
        return d

    def test03_wrap_http_fail(self):
        resource = CardstoriesResource(self.service)
        fail_string = 'FAIL STRING'
        def fail(result, request):
            raise Exception(fail_string)
        resource.handle = fail
        self.site = CardstoriesSite(resource, {}, [])
        request = server.Request(self.Channel(self.site), True)
        request.site = self.site
        d = resource.wrap_http(request)
        def finish(result):
            self.assertSubstring(fail_string, request.transport.getvalue())
        d.addCallback(finish)
        return d

    def test03_wrap_http_fail_disconnected(self):
        resource = CardstoriesResource(self.service)
        fail_string = 'FAIL STRING'
        def fail(result, request):
            raise Exception(fail_string)
        resource.handle = fail
        self.site = CardstoriesSite(resource, {}, [])
        request = server.Request(self.Channel(self.site), True)
        request.site = self.site
        request._disconnected = True
        d = resource.wrap_http(request)
        def finish(result):
            self.assertSubstring('', request.transport.getvalue())
        d.addCallback(finish)
        return d

    def test04_handle(self):
        resource = CardstoriesResource(self.service)
        self.site = CardstoriesSite(resource, {}, [])
        request = server.Request(self.Channel(self.site), True)

        request.method = 'GET'
        self.assertEquals('handle', resource.handle(True, request))

        request.method = 'POST'
        self.assertEquals('handle', resource.handle(True, request))

    def test04_handle_non_internal(self):
        def mock_handle(result, args, internal_request=False):
            return internal_request
        self.service.handle = mock_handle

        resource = CardstoriesResource(self.service)
        self.site = CardstoriesSite(resource, {}, [])
        request = server.Request(self.Channel(self.site), True)

        request.method = 'GET'
        self.assertEquals(False, resource.handle(True, request))

        request.method = 'POST'
        self.assertEquals(False, resource.handle(True, request))

class CardstoriesInternalResourceTest(unittest.TestCase):

    class Transport:
        host = None

        def getPeer(self):
            return None
        def getHost(self):
            return self.host

    class Channel:
        def __init__(self, site):
            self.transport = CardstoriesInternalResourceTest.Transport()
            self.site = site

        def requestDone(self, request):
            pass

    def setUp(self):
        self.service = CardstoriesServiceMockup()

    def tearDown(self):
        if hasattr(self, 'site'):
            self.site.stopFactory()

    @defer.inlineCallbacks
    def test04_handle_internal(self):
        def mock_handle(result, args, internal_request=False):
            return internal_request
        self.service.handle = mock_handle

        self.service.settings['internal-secret'] = 'secret thing'

        resource = CardstoriesInternalResource(self.service)
        self.site = CardstoriesSite(resource, {}, [])

        # Works with good secret param.
        request = server.Request(self.Channel(self.site), True)
        request.method = 'GET'
        request.args = {'secret': ['secret thing']}
        self.assertEquals(True, resource.handle(True, request))

        request = server.Request(self.Channel(self.site), True)
        request.method = 'POST'
        request.args = {'secret': ['secret thing']}
        self.assertEquals(True, resource.handle(True, request))

        # Fails when secret param is bad or doesn't exists.
        request = server.Request(self.Channel(self.site), True)
        request.method = 'GET'
        request.args = {'secret': ['hahahahaha']}
        result = yield resource.handle(True, request)
        self.assertEquals({'error': {'code': 'UNAUTHORIZED'}}, result)

        request = server.Request(self.Channel(self.site), True)
        request.method = 'POST'
        request.args = None
        result = yield resource.handle(True, request)
        self.assertEquals({'error': {'code': 'UNAUTHORIZED'}}, result)


class AGPLResourceTest(unittest.TestCase):

    def setUp(self):
        if os.path.exists('cardstories.zip'):
            os.unlink('cardstories.zip')
        self.service = CardstoriesServiceMockup()

    def tearDown(self):
        if hasattr(self, 'site'):
            self.site.stopFactory()

    def test00_render(self):
        tree = CardstoriesTree(self.service)
        request = DummyRequest(['agpl'])
        child = resource.getChildForRequest(tree, request)
        self.assertTrue(isinstance(child, AGPLResource))
        d = _render(child, request)
        def finish(result):
            self.assertEquals('PK', request.written[0][:2])
        d.addCallback(finish)
        return d

    def test01_agpl(self):
        import cardstories
        import zipfile
        self.assertFalse(os.path.exists('cardstories.zip'))
        r = AGPLResource('.', cardstories)
        r.update()
        self.assertTrue(os.path.exists('cardstories.zip'))
        a = zipfile.ZipFile('cardstories.zip')
        self.assertEquals(a.getinfo('__init__.py').filename, '__init__.py')

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test03"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesSiteTest))
    suite.addTest(loader.loadClass(CardstoriesResourceTest))
    suite.addTest(loader.loadClass(CardstoriesInternalResourceTest))
    suite.addTest(loader.loadClass(AGPLResourceTest))

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
# compile-command: "python-coverage -e ; PYTHONPATH=.. python-coverage -x test_site.py ; python-coverage -m -a -r ../cardstories/site.py"
# End:
