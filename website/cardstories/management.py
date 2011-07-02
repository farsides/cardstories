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

def update_users(sender, app, created_models, verbosity, interactive, **kwargs):
    model_names = [m.__name__ for m in created_models]
    if not interactive \
       or app.__name__ != 'django.contrib.auth.models' \
       or "User" not in model_names:
        return
    
    message = """
You are using django.contrib.auth.  Do you want cardstories to alter the username
column to allow 75 characters? (yes/no): """
    answer = raw_input(message)
    while not answer.lower() in ('y', 'n', 'yes', 'no'):
        answer = raw_input("Please enter either \"yes\" or \"no\": ")
        
    if answer.lower() in ('y', 'yes'):
        cursor = connection.cursor()
        cursor.execute("ALTER TABLE auth_user MODIFY COLUMN username varchar(75) NOT NULL")
    
# sqlite3 does not support ALTER TABLE.
if connection.settings_dict['ENGINE'] != 'django.db.backends.sqlite3':
    post_syncdb.connect(update_users)
