#!/usr/bin/python
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

import os, sys

from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import get_template
from django.template import Context


# Django environment #########################################################

sth=os.path.abspath('..')
sys.path.append(sth)
os.environ['DJANGO_SETTINGS_MODULE'] = 'website.settings'

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')


# Functions ##################################################################

def send_mailing():
    # SMTP begin
    smtp = get_connection(fail_silently=False)
    smtp.open()

    # Headers
    from_email = 'Card Stories <feedback@farsides.com>'
    to_emails = ['xavier@antoviaque.org']
    subject = 'Test templating'

    # Body templates
    d = Context({ 'username': 'Mr Test' })
    text_content = get_template('mail/email_activity.txt').render(d)
    html_content = get_template('mail/email_activity.html').render(d)

    # MIME
    msg = EmailMultiAlternatives(subject, text_content, from_email, to_emails,
                                 headers = { 'Reply-To': 'another@example.com' })
    msg.attach_alternative(html_content, "text/html")
    msg.attach_file(os.path.join(TEMPLATES_DIR, 'test.jpg'))

    # SMTP end
    smtp.send_messages([msg])
    smtp.close()


# Main #######################################################################

if __name__ == '__main__':
    send_mailing()

