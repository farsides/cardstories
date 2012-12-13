#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Farsides <contact@farsides.com>
#
# Authors:
#          Matjaz Gregoric <mtyaka@gmail.com>
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
import sqlite3
from datetime import datetime, timedelta

from django.core.urlresolvers import reverse

# Allow to reference the root dir
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, ROOT_DIR)

import website.cardstories.views
from mailing import send, aggregate


# Functions ##################################################################

def iso_to_datetime(iso_string):
    '''
    Parses datetime string in ISO(?) format as returned by the sqlite module
    and returns a datetime object.
    '''
    return datetime.strptime(iso_string, '%Y-%m-%d %H:%M:%S')

def should_send_email(last_active, game_activities_24h):
    '''
    Returns True if email should be sent to player who was last active
    `last_active` time ago and whose games have seen activities gathered
    in `game_activities_24h` during the last 24 hours.
    '''

    now = datetime.now()
    # Number of days since the player has been last active:
    active_days_ago = (now - iso_to_datetime(last_active)).days

    # If the user was last active within 24 hours, or 7 days ago,
    # we want to send him an email.
    if active_days_ago in [0, 7]:
        should_send = True
    # We also want to send an email every 30 days since he was last active.
    elif active_days_ago % 30 == 0:
        should_send = True
    # If none of the above is true, we still want to send him an email
    # if there was any activity on any of his games within the last 24 hours.
    elif len(game_activities_24h) > 0:
        should_send = True
    # Else just don't send an email today.
    else:
        should_send = False

    return should_send

def get_context(cursor, player_id, game_ids, last_active):
    game_activities = aggregate.get_game_activities(cursor, game_ids, player_id, happened_since=last_active)
    available_games = aggregate.get_available_games(cursor, created_since=last_active, exclude_game_ids=game_ids)
    completed_games = aggregate.get_completed_games(cursor, completed_since=last_active, exclude_game_ids=game_ids)
    unsubscribe_path = reverse(website.cardstories.views.activity_notifications_unsubscribe)

    context = {'game_activities': game_activities,
               'available_games': available_games,
               'completed_games': completed_games,
               'unsubscribe_path': unsubscribe_path}

    return context

def is_context_empty(context):
    '''Returns False if there isn't any valuable information in the context.'''
    for key in ['game_activities', 'available_games', 'completed_games']:
        if len(context[key]) > 0:
            return False
    return True

def loop(ws_db_path, django_db_path, email_list=None, verbose=False):
    django_conn = sqlite3.connect(django_db_path)
    cursor = django_conn.cursor()
    players_list = aggregate.get_all_players(cursor)
    aggregate.seed_playerid2name(players_list)
    cursor.close()
    django_conn.close()

    smtp = send.smtp_open()
    ws_conn = sqlite3.connect(ws_db_path)
    cursor = ws_conn.cursor()

    count = 0

    for id, email, name, unsubscribed in players_list:
        if email_list and not email in email_list:
            continue
        if unsubscribed:
            continue
        game_ids = aggregate.get_player_game_ids(cursor, id)
        last_active = aggregate.get_players_last_activity(cursor, id)
        yesterday = datetime.now() - timedelta(days=1)
        recent_game_activities = aggregate.get_game_activities(cursor, game_ids, id, happened_since=yesterday)

        should_send = should_send_email(last_active, recent_game_activities)
        if should_send:
            context = get_context(cursor, id, game_ids, last_active)
            # Don't send if there isn't any new info in the context.
            if not is_context_empty(context):
                if verbose:
                    print 'Sending email to %s' % email
                send.send_mail(smtp, email, context)
                count += 1

    cursor.close()
    ws_conn.close()
    smtp.close()

    return count


# Main #######################################################################

if __name__ == '__main__':
    if not len(sys.argv) in [3, 4]:
        sys.exit('USAGE: python loop.py path/to/wsdb.sqlite path/to/djangodb.sqlite [path/to/filter.txt]')
    if len(sys.argv) == 4:
        email_list = open(sys.argv[3]).read().splitlines()
    else:
        email_list = None
    print 'Sending emails...'
    count = loop(sys.argv[1], sys.argv[2], email_list=email_list, verbose=True)
    print 'Done!', 'Nr. of emails sent: %d' % count
