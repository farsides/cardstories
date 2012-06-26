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
import re
import datetime

## Django environment
os.environ['DJANGO_SETTINGS_MODULE'] = 'website.settings'

from django.core.mail import get_connection
from django.template.loader import get_template
from django.template import Context
from django.conf import settings

from mailing.multirelated import EmailMultiRelated 

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

    # Headers & templates
    subject = 'Activity on Card Stories! (%s)' % datetime.date.today()
    from_email = 'Card Stories <feedback@farsides.com>'
    to_emails = [email]
    text_template = get_template('mail/email_activity.txt')
    html_template = get_template('mail/email_activity.html')

    context['base_url'] = settings.BASE_URL
    d = Context(context)
    text_content = text_template.render(d)
    html_content = html_template.render(d)

    # MIME
    msg = EmailMultiRelated(subject, text_content, from_email, to_emails)
    msg.attach_alternative(html_content, "text/html")

    # Inline images
    images_filenames = [file for file in os.listdir(TEMPLATES_DIR) 
                        if file.lower().endswith('.png') or
                           file.lower().endswith('.jpg') or
                           file.lower().endswith('.gif')]
    for image_filename in images_filenames:
        msg.attach_related_file(os.path.join(TEMPLATES_DIR, image_filename))
    
    smtp.send_messages([msg])


