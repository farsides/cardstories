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

        # Is welcome mode on?
        self.assertIsNotNone(c.cookies["CARDSTORIES_WELCOME"])


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
        response = c.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Was the user logged in as the cardstories client expects it?
        self.assertIsNotNone(c.cookies["CARDSTORIES_ID"])

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

        # Test successful login of the user, and redirection.
        data = valid_data.copy()
        response = c.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Was the user logged in as the cardstories client expects it?
        self.assertIsNotNone(c.cookies["CARDSTORIES_ID"])

    def test_03getuserid(self):
        """
        Test getuserid. Requires 'users' fixture.

        """
        c = self.client
        base_url = "/getuserid"

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

    def test_04getusername(self):
        """
        Test getuserid.  Requires 'users' fixture.

        """
        c = self.client
        base_url = "/getusername"

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

        # Return proper username for pre-existing user.
        url = "%s/%s/" % (base_url, "1")
        response = c.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, "testuser1@email.com")
