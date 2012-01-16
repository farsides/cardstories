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
# Django settings for website project.
#
import os
import sys

# Shortcuts to the real site directory and its parent.
spath = lambda x: os.path.join(os.path.dirname(__file__), x)
ppath = lambda x: os.path.join(os.path.dirname(
                                     os.path.dirname(__file__)), x)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/cardstories.website',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# A value of None will cause Django to use the same timezone as the operating
# system.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ppath('static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# Avatars' subpaths, relative to the MEDIA_ROOT folder
# (default avatars and users' avatars cache storage URLs)
AVATARS_DEFAULT_SUBPATH = 'css/images/avatars/default/'
AVATARS_CACHE_SUBPATH = 'css/images/avatars/cache/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '^!gqxoef0k9oo%bdri4#aagv@3txu$@voz52zzv_7)ae@8j$%$'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#    'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'website.urls'

TEMPLATE_DIRS = (
        spath('templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'website.cardstories',
    'website.util',
)

# Enables the custom Facebook authentication backend
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'website.cardstories.backends.FacebookBackend'
)

# Enables the custom user profile
AUTH_PROFILE_MODULE = 'cardstories.UserProfile'

# Cardstories settings
CARDSTORIES_HOST = 'localhost:5000'
WEBSERVICE_IP = '127.0.0.1'

# Facebook settings.
FACEBOOK_APP_ID = ''
FACEBOOK_API_SECRET = ''
FACEBOOK_PERMS = ['email']

# Open Web Analytics settings
OWA_ENABLE = False
OWA_URL = ''
OWA_SITE_ID = ''

# Enables code coverage
TEST_RUNNER = 'tests.run_tests_with_coverage'
COVERAGE_MODULES = ['website.cardstories.views',
                    'website.cardstories.forms',
                    'website.cardstories.facebook',
                    'website.cardstories.backends',
                    'website.cardstories.models',
                    'website.cardstories.avatar']

# Use local settings, if any.
try:
    from local_settings import *
except ImportError, e:
    pass
