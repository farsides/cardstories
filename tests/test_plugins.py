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

from cardstories.plugins import CardstoriesPlugins
from cardstories.auth import Auth

class CardstoriesPluginsTest(unittest.TestCase):
    
    def test00_path(self):
        plugins = CardstoriesPlugins({ 'plugins-dir': '..' })
        self.assertEquals(plugins.path('../plugin_one/plugin_one.py'), '../plugin_one/plugin_one.py')
        self.assertEquals(plugins.path('plugin_one'), '../plugin_one/plugin_one.py')
        caught = False
        try:
            plugins.path('WTF')
        except UserWarning, e:
            self.failUnlessSubstring('WTF', e.args[0])
            caught = True
        self.assertTrue(caught)

    def test01_load(self):
        plugins = CardstoriesPlugins({ 'plugins-dir': '..',
                                       'plugins': 'plugin_one plugin_two'})
        class Service:
            def __init__(self):
                self.pollable_plugins = []
        service = Service()
        plugins.load(service)
        self.assertEquals(plugins.plugins[0].service, service)
        self.assertEquals(plugins.plugins[1].service, service)
        self.assertEquals(service.pollable_plugins[0], plugins.plugins[1])
        self.assertEquals(len(service.pollable_plugins), 1)

    def test02_auth_plugin(self):
        '''Auth plugins must be registered on the service object'''
        
        plugins = CardstoriesPlugins({ 'plugins-dir': '..',
                                       'plugins': 'plugin_auth'})
        class Service:
            def __init__(self):
                self.auth = None
        service = Service()
        plugins.load(service)
        self.assertEquals(plugins.plugins[0].service, service)
        self.assertEquals(service.auth, plugins.plugins[0])
        self.assertIsInstance(service.auth, Auth)

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesPluginsTest))

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
# compile-command: "python-coverage -e ; python-coverage -x test_plugins.py ; python-coverage -m -a -r ../cardstories/plugins.py"
# End:
