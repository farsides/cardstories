# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Farsides <contact@farsides.com>
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

import sys, os, json
from mock import Mock

from twisted.trial import unittest, runner, reporter

from plugins.bot import buildwordsscores


# Classes ##################################################################

class BuildWordsScoresTest(unittest.TestCase):

    def test01_build_words_scores(self):
        # Fake environment
        os.environ["DB"] = "DB"
        os.environ["PLUGINS_CONFDIR"] = "../fixture2"

        # Fake db interaction
        buildwordsscores.db = Mock()
        buildwordsscores.db.connect.return_value = mock_connect = Mock()
        mock_connect.cursor.return_value = mock_cursor = Mock()
        mock_cursor.__iter__ = Mock(return_value=iter([[u"Hello, this is a test!"],
                                                       [u"Hello again, testers."],
                                                       [u"Testé the test"]]))

        buildwordsscores.build_words_scores_file()

        with open(buildwordsscores.get_cards_words_scores_filepath()) as f:
            result = json.load(f)
            self.assertEqual(result["1"], {"test": 3, "again": 1, "hello": 2, "tester": 1})

# Main #####################################################################

def Run():
    loader = runner.TestLoader()
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(BuildWordsScoresTest))

    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

