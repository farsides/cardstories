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

## Django environment
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'website.settings'

from django.template.loader import get_template
from django.template import Context
from django.conf import settings

from mailing.multirelated import EmailMultiRelated

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

# Functions ##################################################################

def build_mail(template, subject, to_email, context=None):
    """
    Formats a multipart email using the `template`, which should be
    found in two versions inside the "mail" folder.
    Both a .txt, and a .html version should exist.
    It attaches all images found in the "mail" folder as related files.
    """

    # Headers & templates
    from_email = settings.DEFAULT_FROM_EMAIL
    to_emails = [to_email]
    text_template = get_template('mail/%s.txt' % template)
    html_template = get_template('mail/%s.html' % template)

    context = context or {}
    context['base_url'] = settings.BASE_URL
    c = Context(context)

    text_content = text_template.render(c)
    html_content = html_template.render(c)

    # MIME
    msg = EmailMultiRelated(subject, text_content, from_email, to_emails)
    msg.attach_alternative(html_content, 'text/html')

    # Inline images
    for dirname in ['common', template]:
        filenames = os.listdir(os.path.join(TEMPLATES_DIR, 'images', dirname))

        images_filenames = [file for file in filenames
                            if file.lower().endswith('.png') or
                               file.lower().endswith('.jpg') or
                               file.lower().endswith('.gif')]
        for image_filename in images_filenames:
            msg.attach_related_file(os.path.join(TEMPLATES_DIR, 'images', dirname, image_filename))

    return msg
