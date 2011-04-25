#!/usr/bin/env python
#
# Copyright (C) 2011 Dachary <loic@dachary.org>
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

import os, re
from distutils.core import setup

data_files = []
for dirpath, dirnames, filenames in os.walk('static'):
	    # Ignore dirnames that start with '.'
	    for i, dirname in enumerate(dirnames):
	        if dirname.startswith('.'): del dirnames[i]
                if dirname == 'mockups': del dirnames[i]
	    if filenames:
                filenames = filter(lambda f: re.match('.*.(css|js|html|png)$', f), filenames)
	        data_files.append(['/usr/share/cardstories/' + dirpath.replace('static',''), [os.path.join(dirpath, f) for f in filenames]])

data_files.append(['/etc/default', ['etc/default/cardstories']])
data_files.append(['/etc/cardstories/twisted/plugins', ['etc/cardstories/twisted/plugins/twisted_cardstories.py']])
data_files.append(['/usr/share/cardstories/conf', [ 'conf/nginx.conf' ]])

setup(name='cardstories',
      version='1.0.2',
      requires=['twisted (>=10.1.0)'],
      description='Find out a card using a sentence made up by another player',
      author='Loic Dachary',
      author_email='loic@dachary.org',
      url='http://cardstori.es/',
      license='GNU AGPLv3+',
      data_files=data_files,
      packages=['cardstories'])
