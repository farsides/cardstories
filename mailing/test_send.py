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

from mock import Mock

from twisted.trial import unittest, runner, reporter
from mailing import send


# Classes ##################################################################

class MailingTest(unittest.TestCase):

    def test01_send_mail(self):
        # Capture sent emails
        mock_smtp = Mock()
        self.msg_list = None
        def send_messages(msg_list):
            self.msg_list = msg_list
        mock_smtp.send_messages.side_effect = send_messages

        context = {
                'available_games': [{'game_id': 6161, 'owner_name': u'david', 'sentence': u'this is an available story çà'}], 
                'completed_games': [{'game_id': 6162, 'owner_name': u'goliath', 'sentence': u'this is a completed story éè'}], 
                'game_activities': [{'game_id': 6159, 'state': u'vote', 'owner_name': 'You', 'events': [u'emzie3001 voted', u'Cathy Jewson voted', u'Kazzi voted', u'nara voted', u'Matjaz voted'], 'sentence': u'story with activity ù'}], 
                'unsubscribe_path': '/unsubscribe-path'
            }

        send.send_mail(mock_smtp, 'test@example.com', context)
        mock_smtp.send_messages.assert_called_once()
        mock_smtp.reset_mock()

        self.assertEqual(len(self.msg_list), 1)
        msg_formatted = str(self.msg_list[0].message())
        
        self.assertTrue('From: Card Stories <feedback@farsides.com>' in msg_formatted)
        self.assertTrue('Content-Type: text/plain' in msg_formatted)
        self.assertTrue('Content-Type: text/html' in msg_formatted)
        self.assertTrue('Content-Type: image/jpeg' in msg_formatted)
        self.assertTrue("Content-Disposition: inline; filename=\"umbrella.png\"\nContent-Type: image/png; name=\"umbrella.png\"\nContent-ID: <umbrella.png>" in msg_formatted)
        self.assertTrue('"story with activity =C3=B9" (Game Master: You, State: vote)' in msg_formatted)
        self.assertTrue("\"this is an available story =C3=A7=C3=A0\" (Game Master: david)" in msg_formatted)
        self.assertTrue("\"this is a completed story =C3=A9=C3=A8\" (Game Master: goliath)" in msg_formatted)
        self.assertTrue("emzie3001 voted" in msg_formatted)
        self.assertTrue("/?game_id=3D6161" in msg_formatted)
        self.assertTrue("/?game_id=3D6162" in msg_formatted)
        self.assertTrue("/?game_id=3D6159" in msg_formatted)
        self.assertTrue("/unsubscribe-path" in msg_formatted)

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

