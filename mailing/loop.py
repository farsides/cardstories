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

# Allow to reference the root dir
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, ROOT_DIR)

from mailing import send, aggregate


# Functions ##################################################################

def should_send(player_id, last_active):
    # TODO: Only send if the player didn't opt out.
    # TODO: Only send if player satisfies one of the conditions listed in:
    #       http://tickets.farsides.com/issues/942
    return True

def get_context(cursor, player_id, last_active):
    game_ids = aggregate.get_player_game_ids(cursor, player_id)
    game_activities = aggregate.get_game_activities(cursor, game_ids, player_id, happened_since=last_active)
    available_games = aggregate.get_available_games(cursor, created_since=last_active, exclude_game_ids=game_ids)
    completed_games = aggregate.get_completed_games(cursor, completed_since=last_active, exclude_game_ids=game_ids)
    unsubscribe_url = aggregate.get_unsubscribe_url(player_id);

    context = {'game_activities': game_activities,
               'available_games': available_games,
               'completed_games': completed_games,
               'unsubscribe_url': unsubscribe_url}

    return context

def loop(ws_db_path, django_db_path):
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
    for id, email, name in players_list:
        last_active = aggregate.get_players_last_activity(cursor, id)
        if should_send(id, last_active):
            context = get_context(cursor, id, last_active)
            print 'Sending email to %s' % email
            send.send_mail(smtp, email, context)
            count += 1

    cursor.close()
    ws_conn.close()
    smtp.close()

    return count


# Main #######################################################################

if __name__ == '__main__':
    if not len(sys.argv) == 3:
        sys.exit('USAGE: python loop.py path/to/wsdb.sqlite path/to/djangodb.sqlite')
    print 'Sending emails...'
    count = loop(sys.argv[1], sys.argv[2])
    print 'Done!', 'Nr. of emails sent: %d' % count
