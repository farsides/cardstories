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

# Imports ##################################################################

import sys, os

# Allow to reference the root dir
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, ROOT_DIR)

from twisted.trial import unittest, runner, reporter
from mailing import message


# Classes ##################################################################

class MessageTest(unittest.TestCase):

    def test01_send_mail(self):
        template = 'email_activity'
        subject = 'Hello There!'
        to_email = 'hithere@cardstories.com'
        mail = message.build_mail(template, subject, to_email)
        msg = str(mail.message())

        self.assertTrue('Subject: Hello There!' in msg)
        self.assertTrue('To: hithere@cardstories.com' in msg)
        self.assertTrue('From: Card Stories <feedback@farsides.com>' in msg)
        self.assertTrue('Content-Type: text/plain' in msg)
        self.assertTrue('Content-Type: text/html' in msg)
        self.assertTrue('Content-Type: image/jpeg' in msg)
        self.assertTrue("Content-Disposition: inline; filename=\"umbrella.png\"\nContent-Type: image/png; name=\"umbrella.png\"\nContent-ID: <umbrella.png>" in msg)

# Main #####################################################################

def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(MessageTest))

    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

