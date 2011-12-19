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
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from website.cardstories.facebook import GraphAPI

class FacebookBackend(ModelBackend):
    """ 
    A backend that authenticates and registers a Facebook user locally.
    Requires requesting the 'email' permission for the access token. 
    
    """
    def authenticate(self, token=None):
        api = GraphAPI(token)
        me = api.get('me')
        if me.get('email'):
            user, created = User.objects.get_or_create(username=me['email'])

            # If the user was just created, add relevant info to his local
            # profile.
            if created:
                user.set_unusable_password()
                user.email = me['email']
                
            # Data can change on Facebook, or the user can have logged in
            # without Facebook before
            if me.get('name'):
                user.first_name = me['name']
            user.save()

            # Also save the user's Facebook id to the custom profile.
            profile = user.get_profile()
            profile.facebook_id = me['id']
            profile.save()

            return user

        return None
