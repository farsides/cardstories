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
from django.test import TestCase

class CardstoriesTest(TestCase):
    fixtures = ['users.json']

    def test_00welcome(self):
        c = self.client
        response = c.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('registration_form' in response.context)
        self.assertTrue('login_form' in response.context)

    def test_01registration(self):
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

        # Try to create the user again: this should fail with a form error.
        response = c.post(url, data)
        self.assertFormError(response, form, "username", "This email address is already in use.")

    def test_02login(self):
        """
        Test login.  Requires 'users' fixture to be loaded.

        """
        c = self.client
        url = "/login/"
        form = "login_form"
        valid_data = {"username": "testuser1@email.com",
                      "password": "abc!@#"}

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
        response = c.get(url, data)
        self.assertEqual(response.status_code, 302)

        # Checks user was created properly
        from django.contrib.auth.models import User
        user = User.objects.get(username=fb_email)
        self.assertEqual(user.first_name, fb_name)
        self.assertEqual(user.get_profile().facebook_id, fb_id)

    def test_04get_player_id(self):
        """
        Test getuserid. Requires 'users' fixture.

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
        Test getusername. Requires 'users' fixture.

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
        Test getuseremail. Requires 'users' fixture.

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

        # Return proper email for pre-existing user.
        url = "%s/%s/" % (base_url, "1")
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, "testuser1@email.com")

    def test_07get_loggedin_player_id(self):
        """
        Test getloggedinuserid.  Requires 'users' fixture.

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
