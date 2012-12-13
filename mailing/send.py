# -*- coding: utf-8 -*-
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

# Imports ####################################################################

import os
import datetime

from django.core.mail import get_connection

import mailing.message

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

# Functions ##################################################################

def smtp_open():
    """
    Opens a connection to the SMTP server
    Returns the connection object (Django)
    """
    smtp = get_connection(fail_silently=False)
    smtp.open()
    return smtp

def send_mail(smtp, email, context):
    """
    Formats an activity notification email based on a game activity context,
    and sends to the provided email through an open smtp connection
    """
    subject = 'Activity on Card Stories! (%s)' % datetime.date.today()
    msg = mailing.message.build_mail('email_activity', subject, email, context)
    smtp.send_messages([msg])
