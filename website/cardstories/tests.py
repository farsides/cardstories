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

# Imports ####################################################################

from django.test import TestCase
from django.conf import settings

from website.util.helpers import mkdir_p
        
import shutil, os.path
from mock import Mock, patch


# Tests ######################################################################

class CardstoriesTest(TestCase):
    fixtures = ['users.json']

    def test_00welcome(self):
        c = self.client
        response = c.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('registration_form' in response.context)
        self.assertTrue('login_form' in response.context)

    @patch('website.cardstories.views.GravatarAvatar')
    def test_01registration(self, MockGravatarAvatar):
        """
        Test user registration.

        """
        c = self.client
        url = "/register/"
        form = "registration_form"
        valid_password = "sldfi328@#$"
        valid_data = {"name": "Test User",
                      "username": "testuser@email.com",
                      "password1": valid_password,
                      "password2": valid_password}
        
        # Dont' try to update the avatar
        mock_avatar = Mock()
        MockGravatarAvatar.return_value = mock_avatar
        
        # Empty get.
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('registration_form' in response.context)

        # "name" is required.
        data = valid_data.copy()
        data["name"] = ""
        response = c.post(url, data)
        self.assertFormError(response, form, "name", "This field is required.")

        # "name" must be changed from the default.
        data["name"] = "Your name"
        response = c.post(url, data)
        self.assertFormError(response, form, "name", "Please enter a real name.")

        # "username" is required.
        data = valid_data.copy()
        data["username"] = ""
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "This field is required.")

        # "username" must be changed from the default.
        data["username"] = "your@email.com"
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "Please enter a real email address.")

        # "username" must be an email address.
        data["username"] = "not_a_valid_email"
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "Enter a valid e-mail address.")

        # "username" must not contain over 75 characters.
        data["username"] = "%s@email.com" % ("a" * 70)
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "Ensure this value has at most 75 characters (it has 80).")

        # Passwords must match.
        data = valid_data.copy()
        data["password1"] = "bogus"
        response = c.post(url, data)
        self.assertFormError(response, form, "password1", "The password fields did not match.")

        # Test successful creation of the user, and redirection.
        data = valid_data.copy()
        query = '?game_id=1'
        response = c.post(url + query, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/' + query)

        # Check that the avatar is retreived
        from django.contrib.auth.models import User
        user = User.objects.get(username=valid_data['username'])
        MockGravatarAvatar.assert_called_once_with(user)
        mock_avatar.update.assert_called_once_with()

        # Try to create the user again: this should fail with a form error.
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "This email address is already in use.")

    @patch('website.cardstories.views.GravatarAvatar')
    def test_02login(self, MockGravatarAvatar):
        """
        Test login.  Requires 'users' fixture to be loaded.

        """
        c = self.client
        url = "/login/"
        form = "login_form"
        valid_data = {"username": "testuser1@email.com",
                      "password": "abc!@#"}

        # Dont' try to update the avatar
        mock_avatar = Mock()
        MockGravatarAvatar.return_value = mock_avatar
        
        # Empty get.
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('login_form' in response.context)

        # "username" is required.
        data = valid_data.copy()
        data["username"] = ""
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "This field is required.")

        # "username" must be an email address.
        data["username"] = "not_a_valid_email"
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "Enter a valid e-mail address.")

        # Login in with an inexistent user.
        data["username"] = "bogus@email.com"
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "User not found.")

        # Login in with an inactive user.
        data["username"] = "testuser3@email.com"
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "This account is inactive.")

        # Login in with an invalid password.
        data = valid_data.copy()
        data["password"] = "bogus"
        response = c.post(url, data)
        self.assertFormError(response, form, "password", "Invalid password.")

        # Test successful login of the user, and redirection maintaining game_id.
        data = valid_data.copy()
        query = '?game_id=1'
        response = c.post(url + query, data)
        self.assertTrue('_auth_user_id' in c.session)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'http://testserver/' + query)
        
        # Check that the avatar is retreived
        from django.contrib.auth.models import User
        user = User.objects.get(username=valid_data['username'])
        MockGravatarAvatar.assert_called_once_with(user)
        mock_avatar.update.assert_called_once_with()

    def test_02logout(self):
        '''
        Test logout
        '''

        c = self.client
        data = {"username": "testuser1@email.com",
                "password": "abc!@#"}

        # Initial state - anonymous
        self.assertFalse('_auth_user_id' in c.session)

        # Login
        response = c.post('/login/', data)
        self.assertTrue('_auth_user_id' in c.session)

        # Logout
        response = c.get('/logout/')
        self.assertFalse('_auth_user_id' in c.session)

    def test_03facebook(self):
        """
        Test facebook login and registration.

        """
        from website.cardstories import views
        from website.cardstories import facebook

        fb_id = 123456789
        fb_email = 'bogusdude@cardstories.org'
        fb_name = 'Bogus Dude'

        c = self.client
        url = "/facebook/"

        # Empty get
        response = c.get(url)
        self.assertEqual(response.status_code, 200)

        # User denied access
        data = {'error_reason': 'user_denied',
                'error': 'access_denied',
                'error_description': 'The user denied your request.'}
        response = c.get(url, data)
        self.assertEqual(response.status_code, 200)

        # Token error
        class MockTokenError(object):
            """https://graph.facebook.com/oauth/access_token?..."""
            def read(self):
                return "{" \
                       "\n   \"error\": {" \
                       "\n      \"type\": \"OAuthException\"," \
                       "\n      \"message\": \"Error validating verification code.\"" \
                       "\n   }" \
                       "\n}"
        def mock_token_error(url):
            return MockTokenError()
        views.urlopen = mock_token_error
        data = {'code': 'abcdefghijklmnopqrstuvwxyz'}
        response = c.get(url, data)
        self.assertEqual(response.status_code, 200)

        # GraphAPI parse error
        class MockToken(object):
            """Mocks https://graph.facebook.com/oauth/access_token?..."""
            def read(self):
                # A completely fake access_token
                return "access_token=0123456789|abcdefg|hijklm&expires=1234"
        def mock_token(url):
            return MockToken()
        views.urlopen = mock_token
        class MockMeInvalid(object):
            """Mocks https://graph.facebook.com/me?access_token=..."""
            def read(self):
                return ""
        def mock_me_invalid(url):
            return MockMeInvalid()
        facebook.urlopen = mock_me_invalid
        from simplejson import JSONDecodeError
        with self.assertRaises(JSONDecodeError):
            response = c.get(url, data)

        # GraphAPI exception
        class MockMeAPIException(object):
            """Mocks https://graph.facebook.com/me?access_token=..."""
            def read(self):
                    return "{" \
                           "\n   \"error\": {" \
                           "\n      \"type\": \"OAuthException\"," \
                           "\n      \"message\": \"Invalid access token signature.\"" \
                           "\n   }" \
                           "\n}"
        def mock_me_exception(url):
            return MockMeAPIException()
        facebook.urlopen = mock_me_exception
        with self.assertRaises(facebook.GraphAPIError):
            response = c.get(url, data)

        # No email permission
        class MockMeNoEmail(object):
            """Mocks https://graph.facebook.com/me?access_token=..."""
            def read(self):
                    # A valid return with just basic permissions.
                    return "{" \
                           "\n   \"id\": \"%d\"," \
                           "\n   \"name\": \"%s\"," \
                           "\n   \"first_name\": \"Bogus\"," \
                           "\n   \"last_name\": \"Dude\"," \
                           "\n   \"link\": \"https://www.facebook.com/bogusdude\"," \
                           "\n   \"username\": \"bogusdude\"," \
                           "\n   \"gender\": \"male\"," \
                           "\n   \"timezone\": -3," \
                           "\n   \"locale\": \"en_US\"," \
                           "\n   \"verified\": true," \
                           "\n   \"updated_time\": \"2011-07-15T02:22:58+0000\"" \
                           "\n}" % (fb_id, fb_name)
        def mock_me_noemail(url):
            return MockMeNoEmail()
        facebook.urlopen = mock_me_noemail
        response = c.get(url, data)
        self.assertEqual(response.status_code, 200)

        # Valid user
        class MockMe(object):
            """Mocks https://graph.facebook.com/me?access_token=..."""
            def read(self):
                    # A valid return with basic and email permissions.
                    return "{" \
                           "\n   \"id\": \"%d\"," \
                           "\n   \"name\": \"%s\"," \
                           "\n   \"first_name\": \"Bogus\"," \
                           "\n   \"last_name\": \"Dude\"," \
                           "\n   \"link\": \"https://www.facebook.com/bogusdude\"," \
                           "\n   \"username\": \"bogusdude\"," \
                           "\n   \"gender\": \"male\"," \
                           "\n   \"email\": \"%s\"," \
                           "\n   \"timezone\": -3," \
                           "\n   \"locale\": \"en_US\"," \
                           "\n   \"verified\": true," \
                           "\n   \"updated_time\": \"2011-07-15T02:22:58+0000\"" \
                           "\n}" % (fb_id, fb_name, fb_email)
        def mock_me(url):
            return MockMe()
        facebook.urlopen = mock_me
        
        # Dont' try to update the avatar
        mock_avatar = Mock()
        views.FacebookAvatar = Mock(return_value=mock_avatar)
        
        response = c.get(url, data)
        self.assertEqual(response.status_code, 302)

        # Checks user was created properly
        from django.contrib.auth.models import User
        user = User.objects.get(username=fb_email)
        self.assertEqual(user.first_name, fb_name)
        self.assertEqual(user.get_profile().facebook_id, fb_id)
        
        # Check that fb login/register updates the avatar
        views.FacebookAvatar.assert_called_once_with(user)
        mock_avatar.update.assert_called_once_with()

    def test_04get_player_id(self):
        """
        Test get_player_id. Requires 'users' fixture.

        """
        c = self.client
        base_url = "/get_player_id"

        # Empty request must 404.
        url = "%s/%s/" % (base_url, "")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Try to get a user that doesn't exist.
        url = "%s/%s/" % (base_url, "testuser@email.com")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # User not found, try to create with invalid email.
        url = "%s/%s/" % (base_url, "not_a_valid_email")
        data = {"create": "yes"}
        response = c.get(url, data)
        self.assertEqual(response.status_code, 400)

        # User not found, try to create with email that is over 75 characters
        # long.
        email = "%s@email.com" % ("a" * 70)
        url = "%s/%s/" % (base_url, email)
        data = {"create": "yes"}
        response = c.get(url, data)
        self.assertEqual(response.status_code, 400)

        # User not found, create with valid email.
        url = "%s/%s/" % (base_url, "testuser@email.com")
        data = {"create": "yes"}
        response = c.get(url, data)
        self.assertEqual(response.status_code, 200)

        # Return proper user id for pre-existing user.
        url = "%s/%s/" % (base_url, "testuser1@email.com")
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._container[0], 1)

        # Return proper user id for pre-existing user, while also trying to
        # create.
        url = "%s/%s/" % (base_url, "testuser2@email.com")
        data = {"create": "yes"}
        response = c.get(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._container[0], 2)

    def test_05get_player_name(self):
        """
        Test get_player_name. Requires 'users' fixture.

        """
        c = self.client
        base_url = "/get_player_name"

        # Empty request must 404.
        url = "%s/%s/" % (base_url, "")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Try to get a user with invalid id format.
        url = "%s/%s/" % (base_url, "4adfe$#")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Try to get a user that doesn't exist.
        url = "%s/%s/" % (base_url, "4")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Return proper name for pre-existing user.
        url = "%s/%s/" % (base_url, "1")
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, "Test User 1")

        # Returns an "inferred" name based on first part of email.
        url = "%s/%s/" % (base_url, "3")
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, "testuser3")

    def test_06get_player_email(self):
        """
        Test get_player_email. Requires 'users' fixture.

        """
        c = self.client
        base_url = "/get_player_email"

        # Empty request must 404.
        url = "%s/%s/" % (base_url, "")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Try to get a user with invalid id format.
        url = "%s/%s/" % (base_url, "4adfe$#")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Try to get a user that doesn't exist.
        url = "%s/%s/" % (base_url, "4")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)
        
        # Make sure only the WS can request an email
        default_webservice_ip = settings.WEBSERVICE_IP
        settings.WEBSERVICE_IP = '127.0.0.2'
        url = "%s/%s/" % (base_url, "1")
        response = c.get(url)
        self.assertEqual(response.status_code, 403)
        settings.WEBSERVICE_IP = default_webservice_ip

        # Return proper email for pre-existing user.
        url = "%s/%s/" % (base_url, "1")
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, "testuser1@email.com")

    def test_07get_loggedin_player_id(self):
        """
        Test get_loggedin_player_id.  Requires 'users' fixture.

        """
        c = self.client
        base_url = "/get_loggedin_player_id"
        username = "testuser1@email.com"

        # First, log an user in to get his sessionid
        login_url = "/login/"
        login_form = "login_form"
        login_data = {"username": username,
                      "password": "abc!@#"}

        response = c.post(login_url, login_data)
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(c.cookies["sessionid"])

        # Store sessionid, but delete the cookie for subsequent requests.
        sessionid = c.cookies["sessionid"].value
        del c.cookies["sessionid"]

        # Empty request must 404.
        c = self.client
        url = "%s/%s/" % (base_url, "")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Try to get a user that doesn't exist.
        url = "%s/%s/" % (base_url, "bogus_session_id")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Return proper id for valid sessionid
        url = "%s/%s/" % (base_url, sessionid)
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response._container[0], 1)

    @patch('website.cardstories.views.GravatarAvatar')
    @patch('website.cardstories.views.Avatar')
    def test_08get_player_avatar_url(self, MockAvatar, MockGravatarAvatar):
        """
        Test get_player_avatar_url.  Requires 'users' fixture.

        """
        c = self.client
        base_url = "/get_player_avatar_url"
        avatar_url = 'http://example.com/avatar.jpg'
        player_id = 1
        
        from django.contrib.auth.models import User
        user = User.objects.get(id=player_id)
        
        # Only check that the right Avatar objects/methods are called 
        mock_avatar = Mock()
        mock_gravatar_avatar = Mock()
        MockAvatar.return_value = mock_avatar
        MockGravatarAvatar.return_value = mock_gravatar_avatar
        mock_avatar.get_url.return_value = avatar_url
        mock_gravatar_avatar.get_url.return_value = avatar_url

        # Empty request must 404.
        url = "%s/%s/" % (base_url, "")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Try to get a user with invalid id format.
        url = "%s/%s/" % (base_url, "4adfe$#")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Try to get a user that doesn't exist.
        url = "%s/%s/" % (base_url, "4")
        response = c.get(url)
        self.assertEqual(response.status_code, 404)

        # Return proper avatar_url for pre-existing user
        
        # a) avatar has not been retreived before
        mock_avatar.in_cache.return_value = False
        url = "%s/%d/" % (base_url, player_id)
        response = c.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, avatar_url)
        MockAvatar.assert_called_once_with(user)
        MockGravatarAvatar.assert_called_once_with(user)
        mock_gravatar_avatar.update.assert_called_once_with()

        # b) avatar has been retreived before
        MockGravatarAvatar.reset_mock()
        mock_avatar.in_cache.return_value = True
        url = "%s/%d/" % (base_url, player_id)
        response = c.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, avatar_url)
        self.assertFalse(MockGravatarAvatar.called)

    def set_test_avatar_paths_settings(self):
        """Overrides the current settings to use test environment paths for avatar-related settings"""
        
        test_root = '/tmp/cardstories-test' 
        
        self.default_media_url = settings.MEDIA_URL
        self.default_media_root = settings.MEDIA_ROOT
        self.default_avatars_default_subpath = settings.AVATARS_DEFAULT_SUBPATH
        self.default_avatars_cache_subpath = settings.AVATARS_CACHE_SUBPATH
        
        settings.MEDIA_ROOT = test_root
        settings.MEDIA_URL = '/media'
        settings.AVATARS_CACHE_SUBPATH = 'avatars/cache'
        settings.AVATARS_DEFAULT_SUBPATH = 'avatars/default'
        
        # Make sure the directory on the HD is empty
        shutil.rmtree(test_root, ignore_errors=True)
        
        # Copy default avatars over
        mkdir_p(os.path.join(test_root, 'avatars'))
        shutil.copytree(os.path.join(self.default_media_root, self.default_avatars_default_subpath),
                        os.path.join(settings.MEDIA_ROOT, settings.AVATARS_DEFAULT_SUBPATH))

    def unset_test_avatar_paths_settings(self):
        """Restore test environment settings for avatars paths"""
        
        settings.MEDIA_URL = self.default_media_url
        settings.MEDIA_ROOT = self.default_media_root
        settings.AVATARS_DEFAULT_SUBPATH = self.default_avatars_default_subpath
        settings.AVATARS_CACHE_SUBPATH = self.default_avatars_cache_subpath

    def test_09avatar_get_url(self):
        """Test Avatar.get_url()
        Requires users fixture"""
        
        self.set_test_avatar_paths_settings()
        
        from website.cardstories.avatar import Avatar
        from django.contrib.auth.models import User
        
        player_id = 1
        user = User.objects.get(id=player_id)
        avatar = Avatar(user)
        
        self.assertEqual(avatar.get_url(), '/media/avatars/cache/000/000/1_small.jpg')
        self.assertEqual(avatar.get_url(size='small'), '/media/avatars/cache/000/000/1_small.jpg')
        self.assertEqual(avatar.get_url(size='normal'), '/media/avatars/cache/000/000/1_normal.jpg')
        self.assertEqual(avatar.get_url(size='large'), '/media/avatars/cache/000/000/1_large.jpg')

        self.unset_test_avatar_paths_settings()
        
    def test_09avatar_get_path(self):
        """Test Avatar.get_path()
        Requires users fixture"""
        
        self.set_test_avatar_paths_settings()
        
        from website.cardstories.avatar import Avatar
        from django.contrib.auth.models import User
        
        player_id = 1
        user = User.objects.get(id=player_id)
        avatar = Avatar(user)
        
        self.assertEqual(avatar.get_path(), '/tmp/cardstories-test/avatars/cache/000/000/1_small.jpg')
        self.assertEqual(avatar.get_path(size='small'), '/tmp/cardstories-test/avatars/cache/000/000/1_small.jpg')
        self.assertEqual(avatar.get_path(size='normal'), '/tmp/cardstories-test/avatars/cache/000/000/1_normal.jpg')
        self.assertEqual(avatar.get_path(size='large'), '/tmp/cardstories-test/avatars/cache/000/000/1_large.jpg')
        self.assertEqual(avatar.get_path(size='orig'), '/tmp/cardstories-test/avatars/cache/000/000/1_orig.jpg')
    
        self.unset_test_avatar_paths_settings()
        
    def test_10avatar_in_cache(self):
        """Test Avatar.in_cache()
        Requires users fixture"""
        
        self.set_test_avatar_paths_settings()
        
        from website.cardstories.avatar import Avatar
        from django.contrib.auth.models import User
        
        player_id = 1
        user = User.objects.get(id=player_id)
        avatar = Avatar(user)
        
        self.assertFalse(avatar.in_cache())
        
        mkdir_p('/tmp/cardstories-test/avatars/cache/000/000')
        with open('/tmp/cardstories-test/avatars/cache/000/000/1_small.jpg', 'w') as f:
            f.write('ok')
            
        self.assertTrue(avatar.in_cache())
        
        self.unset_test_avatar_paths_settings()
            
    def test_11avatar_set_to_default(self):
        """Test Avatar.set_to_default()
        Requires users fixture"""
        
        self.set_test_avatar_paths_settings()
        
        from website.cardstories.avatar import Avatar
        from django.contrib.auth.models import User
        
        player_id = 1
        user = User.objects.get(id=player_id)
        avatar = Avatar(user)
        
        avatar.generate_all_sizes = Mock()
        avatar.set_to_default()
        avatar.generate_all_sizes.assert_called_once_with(os.path.join(settings.MEDIA_ROOT,
                                                                       settings.AVATARS_DEFAULT_SUBPATH,
                                                                       '%d.jpg' % player_id))
        self.assertTrue(os.path.isfile('/tmp/cardstories-test/avatars/cache/000/000/%d_orig.jpg' % player_id))
        
        self.unset_test_avatar_paths_settings()
        
    def test_12generate_all_sizes(self):
        """Test Avatar.generate_all_sizes()
        Requires users fixture"""
        
        self.set_test_avatar_paths_settings()
        
        from website.cardstories.avatar import Avatar
        from django.contrib.auth.models import User
        from PIL import Image
        
        player_id = 1
        user = User.objects.get(id=player_id)
        avatar = Avatar(user)
        
        avatar.generate_all_sizes(os.path.join(settings.MEDIA_ROOT,
                                               settings.AVATARS_DEFAULT_SUBPATH,
                                               '%d.jpg' % player_id))
        
        self.assertTrue(os.path.isfile('/tmp/cardstories-test/avatars/cache/000/000/%d_small.jpg' % player_id))
        self.assertTrue(os.path.isfile('/tmp/cardstories-test/avatars/cache/000/000/%d_normal.jpg' % player_id))
        self.assertTrue(os.path.isfile('/tmp/cardstories-test/avatars/cache/000/000/%d_large.jpg' % player_id))
        
        self.assertEqual(Image.open('/tmp/cardstories-test/avatars/cache/000/000/%d_small.jpg' % player_id).size,
                         (avatar.sizes['small'], avatar.sizes['small']))
        self.assertEqual(Image.open('/tmp/cardstories-test/avatars/cache/000/000/%d_normal.jpg' % player_id).size,
                         (avatar.sizes['normal'], avatar.sizes['normal']))
        self.assertEqual(Image.open('/tmp/cardstories-test/avatars/cache/000/000/%d_large.jpg' % player_id).size,
                         (avatar.sizes['large'], avatar.sizes['large']))
        
        self.unset_test_avatar_paths_settings()
            
    def test_13avatar_update_from_response(self):
        """Test Avatar.update_from_response()
        Requires users fixture"""
        
        self.set_test_avatar_paths_settings()
        
        from website.cardstories.avatar import Avatar
        from django.contrib.auth.models import User
        
        player_id = 1
        user = User.objects.get(id=player_id)
        avatar = Avatar(user)
        avatar.generate_all_sizes = Mock()
        avatar.set_to_default = Mock()
        orig_image_path = avatar.get_path(size='orig')
        
        # 404
        response = Mock()
        response.status_code = 404
        avatar.update_from_response(response)
        avatar.set_to_default.assert_called_once_with()
        self.assertFalse(avatar.generate_all_sizes.called)
        avatar.set_to_default.reset_mock()
        
        # Not an image
        response.status_code = 200
        response.headers = {'Content-Type': 'text/html'}
        avatar.update_from_response(response)
        avatar.set_to_default.assert_called_once_with()
        self.assertFalse(avatar.generate_all_sizes.called)
        avatar.set_to_default.reset_mock()
        
        # Got an image
        response.status_code = 200
        response.headers = {'Content-Type': 'image/png'}
        response.content = "image content"
        avatar.update_from_response(response)
        avatar.generate_all_sizes.assert_called_once_with(orig_image_path)
        self.assertFalse(avatar.set_to_default.called)
        self.assertTrue(os.path.isfile(orig_image_path))
        self.assertEqual(open(orig_image_path).read(), "image content")
        
        self.unset_test_avatar_paths_settings()

    def test_14avatar_update(self):
        """Test Avatar.update()
        Requires users fixture"""
        
        from website.cardstories.avatar import Avatar
        
        with self.assertRaises(NotImplementedError):
            Avatar(None).update()
    
    @patch('website.cardstories.avatar.requests')
    def test_15gravatar_avatar_update(self, mock_requests):
        """Test GravatarAvatar.update()
        Requires users fixture"""
        
        from website.cardstories.avatar import GravatarAvatar
        from django.contrib.auth.models import User
        import md5, requests
        
        player_id = 1
        user = User.objects.get(id=player_id)
        user.email = ' Test@Example.com '
        email_hash = md5.new('test@example.com').hexdigest()
        avatar = GravatarAvatar(user)
        avatar.update_from_response = Mock()
        avatar.set_to_default = Mock()

        # OK
        mock_requests.get.return_value = 'result'
        avatar.update()
        mock_requests.get.assert_called_once_with(
                    'http://www.gravatar.com/avatar/%s?d=http://example.com/redirect.jpg&s=255' % email_hash,
                    allow_redirects=False,
                    timeout=avatar.requests_timeout)
        avatar.update_from_response.assert_called_once_with('result')
        self.assertFalse(avatar.set_to_default.called)
        avatar.update_from_response.reset_mock()
        
        # Timeout
        mock_requests.get.side_effect = requests.exceptions.Timeout() 
        avatar.update()
        avatar.set_to_default.assert_called_once_with()
        self.assertFalse(avatar.update_from_response.called)
        
    @patch('website.cardstories.avatar.requests')
    def test_16facebook_avatar_update(self, mock_requests):
        """Test FacebookAvatar.update()
        Requires users fixture"""
        
        from website.cardstories.avatar import FacebookAvatar
        from django.contrib.auth.models import User
        import requests
        
        player_id = 1
        
        user = User.objects.get(id=player_id)
        user_profile = Mock()
        user_profile.facebook_id = '1234'
        user.get_profile = Mock(return_value=user_profile)
        
        avatar = FacebookAvatar(user)
        avatar.update_from_response = Mock()
        avatar.set_to_default = Mock()

        # OK
        mock_requests.get.return_value = 'result'
        avatar.update()
        mock_requests.get.assert_called_once_with(
                    'https://graph.facebook.com/1234/picture?type=large',
                    timeout=avatar.requests_timeout)
        avatar.update_from_response.assert_called_once_with('result')
        self.assertFalse(avatar.set_to_default.called)
        avatar.update_from_response.reset_mock()
        
        # Timeout
        mock_requests.get.side_effect = requests.exceptions.Timeout() 
        avatar.update()
        avatar.set_to_default.assert_called_once_with()
        self.assertFalse(avatar.update_from_response.called)
        
