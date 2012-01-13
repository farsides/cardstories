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

from warnings import warn


class CardstoriesWarning(UserWarning):
    """
    Used for exceptions on the service that are expected to happen
    occassionally. The client will do its best to solve the situation
    appropriately based on the error code and additional data.
    """

    ERROR_CODES = ('GAME_NOT_LOADED', 'GAME_DOES_NOT_EXIST', 'GAME_FULL',
                   'WRONG_STATE_FOR_PICKING', 'WRONG_STATE_FOR_VOTING')

    def __init__(self, code, data={}):
        if code not in self.ERROR_CODES:
            warn('Unknown exception code: %s' % code)
        self.code = code
        self.data = data

    def __str__(self):
        if len(self.data):
            return '%s %s' % (self.code, self.data)
        else:
            return self.code


class CardstoriesException(Exception):
    """
    Used for exceptions that should never happen,
    had everything been running smoothly.
    The client will simply display the error message as received from
    the service.
    """
    pass
