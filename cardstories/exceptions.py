# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Loic Dachary <loic@dachary.org>
#
# Authors:
#          Loic Dachary <loic@dachary.org>
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
    occasionally. The client will do its best to solve the situation
    appropriately based on the error code and additional data.
    """

    def __init__(self, code, data={}):
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
