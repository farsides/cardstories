# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Farsides <contact@farsides.com>
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
from math import ceil

LEVEL_A = 0.5
LEVEL_B = 1.5
LEVEL_C = 3.5

def calculate_level(score):
    """Takes player's score and returns calcualted current level,
    total score needed to reach the next level, and the number of points
    the player still has to gather before reaching the next level."""

    # Players start with score 0 at level 1, and by convention only
    # need one point to reach level 2.
    if not score or score < 0:
        level = 1
        score_next = 1
        score_left = 1

    # Starting at level 2, levels are defined by a "points to the
    # next level" formula, tunable using 3 constants. Precisely
    # due to this tunable nature, levels are not stored on the
    # database, but calculated whenever a request is made.
    else:
        to_next = lambda l: int(ceil(LEVEL_A * l ** 3 + \
                                     LEVEL_B * l ** 2 + \
                                     LEVEL_C * l))
        level = 2
        remainder = score - 1
        score_next = to_next(level)
        while remainder >= score_next:
            remainder -= score_next
            level += 1
            score_next = to_next(level)

        score_left = score_next - remainder

    return level, score_next, score_left

