# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Authors:
#          Matjaz Gregoric <gremat@gmail.com>
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
import os
sys.path.insert(0, os.path.abspath("..")) # so that for M-x pdb works

from twisted.trial import unittest, runner, reporter

from cardstories import levels

# Classes #####################################################################

class CardstoriesLevelsTest(unittest.TestCase):

    def test00_calculate_level(self):
        score = 4112
        level1, score_next1, score_left1 = levels.calculate_level(score)
        self.assertTrue(score_left1 > 0)

        level2, score_next2, score_left2 = levels.calculate_level(score + score_left1)
        self.assertEquals(level2, level1 + 1)
        self.assertEquals(score_next2, score_left2)

# Main ########################################################################

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test12_"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesLevelsTest))
    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)
