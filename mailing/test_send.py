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
sys.path.insert(0, os.path.abspath("..")) # so that for M-x pdb works
from mock import Mock

from twisted.trial import unittest, runner, reporter
from mailing import send


# Classes ##################################################################

class MailingTest(unittest.TestCase):

    def test01_send_mailing(self):
        # Mock the SMTP connection
        mock_smtp = Mock()
        def mock_get_connection(*args, **kargs):
            return mock_smtp
        send.get_connection = mock_get_connection

        # Capture sent emails
        self.msg_list = None
        def send_messages(msg_list):
            self.msg_list = msg_list
        mock_smtp.send_messages.side_effect = send_messages

        send.send_mailing()
        mock_smtp.open.assert_called_once()
        mock_smtp.close.assert_called_once()
        mock_smtp.reset_mock()

        self.assertEqual(len(self.msg_list), 1)
        msg_formatted = str(self.msg_list[0].message())
        self.assertTrue('From: Card Stories <feedback@farsides.com>' in msg_formatted)
        self.assertTrue('Content-Type: multipart/mixed' in msg_formatted)
        self.assertTrue('Content-Type: text/plain' in msg_formatted)
        self.assertTrue('Content-Type: text/html' in msg_formatted)
        self.assertTrue('Content-Type: image/jpeg' in msg_formatted)

# Main #####################################################################

def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(MailingTest))

    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

