#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Extract tracebacks from the Card Stories webservice log
#
# Copyright (C) 2012 Farsides <contact@farsides.com>
#
# Authors:
#          Xavier Antoviaque <xavier@antoviaque.org>
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

import sys, os.path, re


# Main ########################################################################

## Argument extraction ##

if len(sys.argv) < 2:
    sys.exit('Usage: %s /path/to/twisted_log_file.log' % sys.argv[0])

if not os.path.exists(sys.argv[1]):
    sys.exit('ERROR: Log file %s was not found!' % sys.argv[1])

LOG_FILE = sys.argv[1]


## Print out tracebacks ##

tracebacks = ""
in_traceback = False

with open(LOG_FILE) as f:
    for line in f:
        if re.search(r'Traceback', line):
            in_traceback = True
        elif in_traceback and (re.match(r'\t$', line) or re.match(r'[^ ]+ [^ ]+ \[[^\]]+\] [^ -]+', line)):
            tracebacks += "\n==================\n\n"
            in_traceback = False

        if in_traceback:
            tracebacks += line

print tracebacks


