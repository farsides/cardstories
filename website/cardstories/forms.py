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
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django import forms


class CardstoriesForm(forms.Form):
    """
    The base CardStories form.

    """

    def __init__(self, *args, **kwargs):
        """
        Adds a css error class to widgets.

        """
        super(CardstoriesForm, self).__init__(*args, **kwargs)
        if self.errors:
            for f_name in self.fields:
                if f_name in self.errors:
                    classes = self.fields[f_name].widget.attrs.get('class', '')
                    classes += ' error'
                    self.fields[f_name].widget.attrs['class'] = classes


class RegistrationForm(CardstoriesForm):
    """
    The registration form.

    """
    name = forms.CharField(required=True, initial="Your name", max_length=30,
        widget=forms.TextInput(attrs={'class': 'name default'}))
    username = forms.EmailField(required=True, initial="your@email.com", max_length=75,
        widget=forms.TextInput(attrs={'class': 'username default'}))
    password1 = forms.CharField(required=True,
        widget=forms.PasswordInput(attrs={'class': 'password1'}))
    password2 = forms.CharField(required=True,
        widget=forms.PasswordInput(attrs={'class': 'password2'}))

    # The following two fields are simply a way to have default values as
    # field labels, which will later be handled appropriately by some
    # Javascript trickery.
    password1_clear = forms.CharField(required=False, initial="Password",
        widget=forms.TextInput(attrs={'class': 'password1 clear'}))
    password2_clear = forms.CharField(required=False, initial="Confirm password",
        widget=forms.TextInput(attrs={'class': 'password2 clear'}))

    def clean_name(self):
        """
        Validates that the supplied name is real.
        
        """
        if self.cleaned_data["name"] == "Your name":
            errmsg = u"Please enter a real name."
            self._errors["name"] = self.error_class([errmsg])
        return self.cleaned_data["name"]
    
    def clean_username(self):
        """
        Validates that the supplied username is both unique and different from
        the initial value.
        
        """
        # TODO: try to get the initial value from the form definition, instead
        # of hardcoding it here.
        if self.cleaned_data["username"] == "your@email.com":
            errmsg = u"Please enter a real email address."
            self._errors["username"] = self.error_class([errmsg])
        elif User.objects.filter(username__iexact=self.cleaned_data['username']):
            errmsg = u"This email address is already in use."
            self._errors["username"] = self.error_class([errmsg])
        return self.cleaned_data["username"]

    def clean(self):
        """
        Verifies that the passwords match.
        
        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                errmsg = u"The password fields did not match."
                # Only the first password field will be used by the template to
                # display an error message, so there's no need to set the error
                # on the second one too.
                self._errors["password1"] = self.error_class([errmsg])
        return self.cleaned_data


class LoginForm(CardstoriesForm):
    """
    The login form.

    """
    username = forms.EmailField(required=True, initial="your@email.com", max_length=75,
        widget=forms.TextInput(attrs={'class': 'username default'}))
    password = forms.CharField(required=True,
        widget=forms.PasswordInput(attrs={'class': 'password'}))
    return_to = forms.CharField(required=False, widget=forms.HiddenInput())

    # The following field is simply a way to have a default value as a field
    # label, which will later be handled appropriately by some Javascript
    # trickery.
    password_clear = forms.CharField(required=False, initial="Password",
        widget=forms.TextInput(attrs={'class': 'password clear'}))

    def clean(self):
        """
        Tries to authenticate the user.

        """
        if self.cleaned_data.get('username') and self.cleaned_data.get('password'):
            if not User.objects.filter(username__iexact=self.cleaned_data['username']):
                errmsg = u"User not found."
                self._errors["username"] = self.error_class([errmsg])
            else:
                auth_user = authenticate(username=self.cleaned_data['username'],
                                         password=self.cleaned_data['password'])
                if auth_user is not None:
                    if auth_user.is_active:
                        self.auth_user = auth_user
                    else:
                        errmsg = u"This account is inactive."
                        self._errors["username"] = self.error_class([errmsg])
                else:
                    errmsg = u"Invalid password."
                    self._errors["password"] = self.error_class([errmsg])
        return self.cleaned_data
