#
# Copyright (C) 2011 Farsides <contact@farsides.com>
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
from django import template
from django.conf import settings
register = template.Library()

@register.simple_tag
def fb_perms():
    return ",".join(getattr(settings, 'FACEBOOK_PERMS', []))

@register.simple_tag
def fb_like():
    return '<iframe src="//www.facebook.com/plugins/like.php?href=http%3A%2F%2Ffacebook.com%2Fcardstories&amp;send=false&amp;layout=button_count&amp;width=90&amp;show_faces=false&amp;action=like&amp;colorscheme=light&amp;font=arial&amp;height=21&amp;appId=280081805344240" scrolling="no" frameborder="0" style="border:none; overflow:hidden; width:90px; height:21px;" allowTransparency="true"></iframe>'
