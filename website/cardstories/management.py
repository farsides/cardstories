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
from django.db.models.signals import post_syncdb
from django.db import connection
from django.contrib.sites import models as sites_app

def update_username_column(sender, app, created_models, verbosity, interactive, **kwargs):
    """
    Updates username column to 75 characters.  This technique doest not work
    with sqlite databases, so if this backend is detected, this function does
    nothing.

    """
    model_names = [m.__name__ for m in created_models]
    if not interactive \
       or connection.settings_dict['ENGINE'] == 'django.db.backends.sqlite3' \
       or app.__name__ != 'django.contrib.auth.models' \
       or "User" not in model_names:
        return
    
    msg = "\nYou are using django.contrib.auth.  Do you want cardstories " \
          "to alter the username column\nto allow 75 characters? (yes/no): "
    answer = raw_input(msg)
    while not answer.lower() in ('y', 'n', 'yes', 'no'):
        answer = raw_input("Please enter either \"yes\" or \"no\": ")
        
    if answer.lower() in ('y', 'yes'):
        cursor = connection.cursor()
        cursor.execute("ALTER TABLE auth_user MODIFY COLUMN username varchar(75) NOT NULL")

def update_domain_name(sender, app, created_models, verbosity, interactive, **kwargs):
    """
    Updates default domain name.  If non-interactive, uses a sane default that
    is compatible with local Facebook development.

    """
    from django.contrib.sites.models import Site
    if Site in created_models and interactive:
        msg = "\nYou just installed Django's sites system. What domain name " \
                "would you like to use?\nEnter a domain such as \"cardstories.org\": "
        domain = raw_input(msg)

        s = Site.objects.get(id=1)
        s.domain = domain
        s.name = domain
        s.save()

post_syncdb.connect(update_username_column)
post_syncdb.connect(update_domain_name, sender=sites_app)
