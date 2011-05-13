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
from twisted.python import runtime
from twisted.internet import reactor, defer

class pollable:

    def __init__(self, timeout):
        self.timeout = timeout
        self.pollers = []
        self.modified = int(runtime.seconds() * 1000)

    def __del__(self):
        self.destroy()

    def get_modified(self):
        return self.modified

    def set_modified(self, modified):
        self.modified = modified

    def destroy(self):
        pollers = self.pollers
        self.pollers = []
        for poller in pollers:
            poller.callback(None)

    def touch(self, args):
        self.modified = int(runtime.seconds() * 1000)
        pollers = self.pollers
        self.pollers = []
        args['modified'] = [self.modified]
        for poller in pollers:
            poller.callback(args)
        return args

    def poll(self, args):
        modified = int(args['modified'][0])
        if modified < self.modified:
            #
            # something happened since the last poll, no need to wait
            #
            args['modified'] = [self.modified]
            return defer.succeed(args)
        d = defer.Deferred()
        self.pollers.append(d)
        def timeout():
            args['timeout'] = [int(runtime.seconds() * 1000)]
            if d in self.pollers:
                self.pollers.remove(d)
            d.callback(args)
        timer = reactor.callLater(self.timeout, timeout)
        def success(result):
            if d in self.pollers:
                self.pollers.remove(d)
            if result != None:
                result['modified'] = [self.modified]
            if timer.active():
                if result != None:
                    result['active_timer'] = [True]
                timer.cancel()
            return result
        def error(reason):
            if d in self.pollers:
                self.pollers.remove(d)
            if timer.active():
                reason.active_timer = True
                timer.cancel()
            return reason
        d.addCallbacks(success, error)
        return d
