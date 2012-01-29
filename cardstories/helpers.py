# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Farsides <contact@farsides.com>
#
# Authors:
#          Xavier Antoviaque <xavier@antoviaque.org>
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

# Imports ####################################################################

from twisted.internet import defer
from cardstories.exceptions import CardstoriesException


# Classes ####################################################################

class Observable(object):

    def listen(self):
        d = defer.Deferred()
        self.observers.append(d)
        return d

    def notify(self, result):
        if hasattr(self, 'notify_running'):
            raise CardstoriesException, 'recursive call to notify'
        self.notify_running = True
        observers = self.observers
        self.observers = []
        def error(reason):
            reason.printTraceback()
            return True
        d = defer.DeferredList(observers)
        for listener in observers:
            listener.addErrback(error)
            listener.callback(result)
        del self.notify_running
        return d

