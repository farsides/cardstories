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

from twisted.python import log, usage
from twisted.application import internet, service, app
from twisted.web import resource, server
from twisted.cred import portal, checkers
from twisted.conch import manhole, manhole_ssh

#from OpenSSL import SSL

from cardstories.service import CardstoriesService
from cardstories.plugins import CardstoriesPlugins
#from cardstories.service import SSLContextFactory
from cardstories.site import CardstoriesTree, CardstoriesResource, CardstoriesSite

class Options(usage.Options):
    synopsis = "[-h|--help] [-p|--port=<number>] [-s|--ssl-port=<number>] [-P|--ssl-pem=</etc/cardstories/cert.pem>] [-d|--db=</var/lib/cardstories/cardstories.sqlite>] [-v|--verbose]"

    longdesc = "Find out a card using a sentence made up by another player"

    optParameters = [
         ["interface", "i", "127.0.0.1", "Interface to which the server must be bound"],
         ["port", "p", 4923, "Port on which to listen", int],
         ["ssl-port", "s", None, "Port on which to listen for SSL", int],
         ["ssl-pem", "P", "/etc/cardstories/cert.pem", "certificate path name", str],
         ["db", "d", "/var/lib/cardstories/cardstories.sqlite", "sqlite3 game database path", str],
         ["poll-timeout", "", 300, "Number of seconds before a long poll timesout", int],
         ["game-timeout", "", (24 * 60 * 60), "Number of seconds before a game in progress timesout", int],
         ["static", "", "/usr/share/cardstories", "directory where /static files will be fetched", str],
         ["plugins-libdir", "", "/var/lib/cardstories/plugins", "plugins storage directory", str],
         ["plugins-confdir", "", "/etc/cardstories/plugins", "plugins configuration directory", str],
         ["plugins-dir", "", "/usr/share/cardstories/plugins", "plugins directory", str],
         ["plugins-logdir", "", "/var/log/cardstories", "plugins log directory", str],
         ["plugins", "", "", "white space separated list of plugins to load, either a path name of a name in plugins-dir without the trailing .py", str],
         ["plugins-pre-process", "", "", "white space separated list of plugins to rework the incoming HTTP request", str],
         ["plugins-post-process", "", "", "white space separated list of plugins to reworkd the JSON result of a request", str]
    ]

    optFlags = [
        ["verbose", "v", "verbosity level"],
        ["manhole", "", "allow ssh -p 2222 user@127.0.0.1 with password pass to get a manhole shell"]
        ]

def getManholeFactory(namespace, **passwords):
    realm = manhole_ssh.TerminalRealm()
    def getManhole(_):
        return manhole.Manhole(namespace)
    realm.chainedProtocolFactory.protocolFactory = getManhole
    p = portal.Portal(realm)
    p.registerChecker(
       checkers.InMemoryUsernamePasswordDatabaseDontUse(**passwords))
    f = manhole_ssh.ConchFactory(p)
    return f

def makeService(settings):
    service_collection = service.MultiService()
    cardstories_service = CardstoriesService(settings)
    plugins = CardstoriesPlugins(settings)
    plugins.load(cardstories_service)
    cardstories_service.setServiceParent(service_collection)

    site = CardstoriesSite(CardstoriesTree(cardstories_service), settings, plugins.plugins)

    if settings.get('manhole', None):
        internet.TCPServer(2222,
                           getManholeFactory(locals(), user="pass"),
                           interface='127.0.0.1').setServiceParent(service_collection)

    internet.TCPServer(settings['port'],
                       site,
                       interface=settings.get('interface', '127.0.0.1')
                       ).setServiceParent(service_collection)

    # if settings.has_key('ssl-port') and settings['ssl-port']:
    #     internet.SSLServer(settings['ssl-port'], site, SSLContextFactory(settings)
    #                        ).setServiceParent(service_collection)

    return service_collection
