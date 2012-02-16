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

class Lockable(object):
    """
    Allow the object to check that some portions of its code are not executed
    concurrently.
    """

    def lock(self, lock_type='default'):
        """
        Tries to acquire a lock, optionally of a specific type.
        If a lock is already in place, the lock fails
        """

        if not hasattr(self, 'notify_running'):
            self.notify_running = []

        if lock_type in self.notify_running:
            raise CardstoriesException, 'Lock failed - type %s already in use' % lock_type

        self.notify_running.append(lock_type)

    def unlock(self, lock_type='default'):
        """
        Remove the lock of the specified type
        """

        self.notify_running.remove(lock_type)


class Observable(Lockable):

    def listen(self):
        d = defer.Deferred()
        self.observers.append(d)
        return d

    def notify(self, result):
        # Only allow one type of notification to be
        # called at a time, to prevent recursive calls
        self.lock(result['type'])

        observers = self.observers
        self.observers = []
        def error(reason):
            reason.printTraceback()
            return True
        d = defer.DeferredList(observers)
        for listener in observers:
            listener.addErrback(error)
            listener.callback(result)

        self.unlock(result['type'])
        return d

