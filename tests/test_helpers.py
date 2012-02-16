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

# Imports #####################################################################

import sys

from twisted.trial import unittest, runner, reporter

from cardstories.helpers import Lockable, Observable
from cardstories.exceptions import CardstoriesException

# Classes #####################################################################

class CardstoriesLockTest(unittest.TestCase):

    def test01_lock_default(self):
        exception_raised = False

        lock = Lockable()
        lock.lock()
        try:
            lock.lock()
        except CardstoriesException as e:
            exception_raised = True
            self.failUnlessSubstring('Lock failed', e.args[0])

        self.assertEqual(exception_raised, True)

        lock.unlock()
        lock.lock()

    def test01_lock_multiple(self):
        exception_raised = False
        lock_type1 = 'LOCK TYPE 1'
        lock_type2 = 'LOCK TYPE 2'

        lock = Lockable()
        lock.lock(lock_type1)
        lock.lock(lock_type2)
        try:
            lock.lock(lock_type1)
        except CardstoriesException as e:
            exception_raised = True
            self.failUnlessSubstring('Lock failed', e.args[0])

        self.assertEqual(exception_raised, True)

        lock.unlock(lock_type2)
        lock.lock(lock_type2)

# Main ########################################################################

def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesLockTest))
    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

