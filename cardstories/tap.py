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
import sys

from twisted.python import log, usage
from twisted.application import internet, service, app
from twisted.web import resource, server

from OpenSSL import SSL

from cardstories.service import SSLContextFactory, CardstoriesService
from cardstories.site import CardstoriesTree, CardstoriesResource

class Options(usage.Options):
    synopsis = "[-h|--help] [-p|--port=<number>] [-s|--ssl-port=<number>] [-P|--ssl-pem=</etc/cardstories/cert.pem>] [-d|--db=</var/cache/cardstories/cardstories.sqlite>] [-v|--verbose]"

    longdesc = "Find out a card using a sentence made up by another player"

    optParameters = [
         ["interface", "i", "127.0.0.1", "Interface to which the server must be bound"],
         ["port", "p", 4923, "Port on which to listen", int],
         ["ssl-port", "s", None, "Port on which to listen for SSL", int],
         ["ssl-pem", "P", "/etc/cardstories/cert.pem", "certificate path name", str],
         ["db", "d", "/var/cache/cardstories/cardstories.sqlite", "sqlite3 game database path", str],
         ["auth", "a", None, "authentication plugin values : basic", str],
         ["auth-db", "", "/var/cache/cardstories/auth.sqlite", "sqlite3 auth database path", str],
         ["loop", "", -1, "Number of ping batchs to run, -1 means forever, 0 means never", int],
         ["static", "", "/usr/share/cardstories", "directory where /static files will be fetched", str]
    ]

    optFlags = [
        ["verbose", "v", "verbosity level"]
        ]

def makeService(settings):
    service_collection = service.MultiService()
    cardstories_service = CardstoriesService(settings)
    cardstories_service.setServiceParent(service_collection)

    site = server.Site(CardstoriesTree(cardstories_service))

    internet.TCPServer(settings['port'],
                       site,
                       interface=settings.get('interface', '127.0.0.1')
                       ).setServiceParent(service_collection)

    if settings.has_key('ssl-port') and settings['ssl-port']:
        internet.SSLServer(settings['ssl-port'], site, SSLContextFactory(settings)
                           ).setServiceParent(service_collection)

    return service_collection
