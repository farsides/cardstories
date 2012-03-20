#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Author: Xavier Antoviaque <xavier@antoviaque.org>
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

import os.path, hashlib, shutil
import requests
from requests.exceptions import Timeout
from PIL import Image

from django.conf import settings
from website.util.helpers import mkdir_p

# Classes #####################################################################

class Avatar(object):
    """
    Handler for a given user avatar
    Keeps a local cache of any user's avatar on the local hard drive
    """
    
    def __init__(self, user):
        self.user = user
        
        self.nb_default_avatars = 6
        self.sizes = { 'small':   52,
                       'normal': 100,
                       'large':  200 }
        self.requests_timeout = 3 # seconds
        
    def get_subdir_filename(self, size="small"):
        '''The current user's avatar sub-path, relative to MEDIA_ROOT'''
        
        # Make sure the avatar id is a string with enough characters to split it in subdirectories
        user_id_str = "%09d" % self.user.id
        
        avatar_subdir = os.path.join(user_id_str[0:3], user_id_str[3:6])
        avatar_filename = "%d_%s.jpg" % (self.user.id, size)
        
        return avatar_subdir, avatar_filename 
    
    def get_path(self, size="small"):
        '''The full system path to this user's avatar image file'''
        
        avatar_subdir, avatar_filename = self.get_subdir_filename(size=size)
        avatar_dir = os.path.join(settings.MEDIA_ROOT, settings.AVATARS_CACHE_SUBPATH, avatar_subdir)
        mkdir_p(avatar_dir) # Make sure the directory exists
        
        return os.path.join(avatar_dir, avatar_filename)
    
    def get_url(self, size="small"):
        '''The URL to this user's avatar image file'''
        
        avatar_subdir, avatar_filename = self.get_subdir_filename(size=size)
        
        return os.path.join(settings.MEDIA_URL, settings.AVATARS_CACHE_SUBPATH, avatar_subdir, avatar_filename)
    
    def in_cache(self):
        '''Return True if the avatar file exists in the cache for this user, False otherwise'''
        
        avatar_path = self.get_path()
        if os.path.exists(avatar_path):
            return True
        else:
            return False
    
    def update(self):
        '''To subclass - update the self.get_path() image file'''
        
        raise NotImplementedError
        
    def set_to_default(self):
        '''Set the user avatar to his default one'''
        
        default_avatar_nb = self.user.id % self.nb_default_avatars
        default_avatar_path = os.path.join(settings.MEDIA_ROOT, \
                                           settings.AVATARS_DEFAULT_SUBPATH, \
                                           "%d.jpg" % default_avatar_nb)
        shutil.copy(default_avatar_path, self.get_path(size="orig"))
        self.generate_all_sizes(default_avatar_path)
        
    def generate_all_sizes(self, orig_avatar_path):
        '''Takes an avatar image and convert it to each of the sizes in self.sizes, each on a different file'''

        for size, nb_pixels in self.sizes.items():         
            im = Image.open(orig_avatar_path)
            im.thumbnail((nb_pixels, nb_pixels), Image.ANTIALIAS)
            im.save(self.get_path(size=size), "JPEG", quality=95, optimize=True)

    def update_from_response(self, request_response):
        '''Updates the avatar image file from a requests response content 
        Uses the response content if it is JPG image data, use the default avatar otherwise'''
        
        if request_response.status_code == 200 and \
            request_response.headers['Content-Type'].startswith('image/'): # got an avatar
                orig_avatar_path = self.get_path(size="orig") 
                with open(orig_avatar_path, 'wb') as f:
                    f.write(request_response.content)
                self.generate_all_sizes(orig_avatar_path)
        else:
            self.set_to_default()


class GravatarAvatar(Avatar):
    
    def update(self):
        """
        Fetch the avatar from gravatar if available, otherwise use one of the default
        local avatars
        """
    
        email_clean = self.user.email.strip().lower()
        email_md5 = hashlib.md5(email_clean).hexdigest()
        
        # Add a fake default URL to detect when the user has no gravatar image (gravatar will redirect to it)
        gravatar_url = "http://www.gravatar.com/avatar/%s?d=%s&s=255" % \
                                    (email_md5, "http://example.com/redirect.jpg")
        
        try:
            r = requests.get(gravatar_url, allow_redirects=False, timeout=self.requests_timeout)
            self.update_from_response(r)
        except Timeout:
            self.set_to_default()


class FacebookAvatar(Avatar):
     
    def update(self):
        """
        Fetch the avatar from Facebook if possible, otherwise use one of the default
        local avatars
        """
    
        facebook_avatar_url = 'https://graph.facebook.com/%s/picture?type=large' % \
                                                        self.user.get_profile().facebook_id
        
        try:
            r = requests.get(facebook_avatar_url, timeout=self.requests_timeout)
            self.update_from_response(r)
        except Timeout:
            self.set_to_default()

           
