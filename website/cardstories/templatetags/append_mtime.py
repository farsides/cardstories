#
# Copyright (C) 2012 Farsides <contact@farsides.com>
#
# Author: Adolfo R. Brandes <arbrandes@gmail.com>
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
import os
from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def append_mtime(path):
    """ 
    Appends a query parameter with the file's mtime.  Useful for preventing
    browser caching.  TODO: cache file mtimes.

    """
    stripped_path = path
    if path.startswith(settings.MEDIA_URL):
        stripped_path = path[len(settings.MEDIA_URL):]
    full_path = os.path.abspath(os.path.join(settings.MEDIA_ROOT,
                                             stripped_path))
    try:
        mtime = os.path.getmtime(full_path)
        return "%s?%s" % (path, mtime)
    except OSError:
        # If file wasn't found, just return the original path.
        return path
