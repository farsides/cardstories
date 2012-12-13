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
from datetime import datetime, timedelta


# Main ########################################################################

## Argument extraction ##

if len(sys.argv) < 2:
    sys.exit('Usage: %s /path/to/twisted_log_file.log' % sys.argv[0])

if not os.path.exists(sys.argv[1]):
    sys.exit('ERROR: Log file %s was not found!' % sys.argv[1])

LOG_FILE = sys.argv[1]
# Don't look for tracebacks older than one day.
SINCE_DATETIME = datetime.now() - timedelta(1)

## Print out tracebacks ##

tracebacks = ""
in_traceback = False
timestamp = None

with open(LOG_FILE) as f:
    for line in f:
        if re.match(r'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d', line):
            timestamp = datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')


        if timestamp >= SINCE_DATETIME:
            if re.search(r'Traceback', line):
                tracebacks += timestamp.strftime("--- %Y-%m-%d %H:%M:%S ---\n\n")
                in_traceback = True
            elif in_traceback and \
                    (re.match(r'\t$', line) or re.match(r'[^ ]+ [^ ]+ \[[^\]]+\] [^ -]+', line)) and not \
                    (re.search('Failure', line) or re.search('Error', line)):
                tracebacks += "\n==================\n\n"
                in_traceback = False

            if in_traceback:
                tracebacks += line

if not tracebacks:
    tracebacks = "No errors today, good job! : )\n"

print tracebacks
