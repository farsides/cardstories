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

from datetime import datetime, timedelta


GAME_CREATED = 1
GAME_MOVED_TO_VOTING = 2
GAME_COMPLETED = 3
GAME_CANCELED = 4
OWNER_CHOSE_CARD = 5
OWNER_WROTE_STORY = 6
PLAYER_INVITED = 7
PLAYER_JOINED = 8
PLAYER_LEFT = 9
PLAYER_PICKED_CARD = 10
PLAYER_VOTED = 11


# Event logging functions
# -----------------------

# They work with twisted adbapi databse objects.

def log_event(db, event_type, game_id, player_id, data=None):
    sql = "INSERT INTO event_logs (timestamp, player_id, game_id, event_type, data) VALUES (datetime('now'), ?, ?, ?, ?)"
    d = db.runQuery(sql, [player_id, game_id, event_type, data])
    return d

def game_created(db, game_id, author_id):
    log_event(db, GAME_CREATED, game_id, author_id)

def owner_chose_card(db, game_id, author_id, card):
    log_event(db, OWNER_CHOSE_CARD, game_id, author_id, card)

def owner_wrote_story(db, game_id, author_id, sentence):
    log_event(db, OWNER_WROTE_STORY, game_id, author_id, sentence)

def player_invited(db, game_id, author_id, player_id):
    log_event(db, PLAYER_INVITED, game_id, author_id, player_id)

def player_joined(db, game_id, player_id):
    log_event(db, PLAYER_JOINED, game_id, player_id)

def player_picked_card(db, game_id, player_id, card):
    log_event(db, PLAYER_PICKED_CARD, game_id, player_id, card)

def player_voted(db, game_id, player_id, card):
    log_event(db, PLAYER_VOTED, game_id, player_id, card)

def player_left(db, game_id, player_id):
    log_event(db, PLAYER_LEFT, game_id, player_id)

def game_moved_to_voting(db, game_id, author_id):
    log_event(db, GAME_MOVED_TO_VOTING, game_id, author_id)

def game_completed(db, game_id, author_id):
    log_event(db, GAME_COMPLETED, game_id, author_id)

def game_canceled(db, game_id, author_id):
    log_event(db, GAME_CANCELED, game_id, author_id)


# Log query functions
# -------------------

# They work with plain (sync) sqlite3 cursors.

def parse_extra_data(value, event_type):
    '''
    Parses the extra data value (given as a string) according
    to the type of event. If event type doesn't carry any
    extra data returns None.
    '''
    if event_type == OWNER_CHOSE_CARD:
        data = int(value)
    elif event_type == OWNER_WROTE_STORY:
        data = value
    elif event_type == PLAYER_INVITED:
        data = int(value)
    elif event_type == PLAYER_PICKED_CARD:
        data = int(value)
    elif event_type == PLAYER_VOTED:
        data = int(value)
    else:
        data = None

    return data

def get_players_last_activity(cursor, player_id):
    '''
    Finds the last action logged about the player player_id in the
    event_logs table.
    If nothing found, returns None, otherwise returns a dict containing:
    'timestamp', 'game_id', 'event_type', and 'data' keys with corresponding values.
    '''
    sql = """SELECT timestamp, game_id, event_type, data
               FROM event_logs
             WHERE player_id = ?
               ORDER BY timestamp DESC LIMIT 1"""
    cursor.execute(sql, [player_id])
    row = cursor.fetchone()
    if row[0]:
        result = {'timestamp': row[0],
                  'game_id': row[1],
                  'event_type': row[2],
                  'data': parse_extra_data(row[3], row[2])}
    else:
        result = None

    return result

def get_game_activities(cursor, game_id, since=None):
    '''
    Returns all activities for `game_id` that happened since the `since` datetime,
    which defaults to 24 hours ago from now.
    '''
    if since is None:
        since = datetime.now() - timedelta(days = 1) # yesterday
    sql = """SELECT timestamp, player_id, event_type, data
                      FROM event_logs
                    WHERE game_id = ? AND timestamp > ?
                      ORDER BY timestamp"""
    cursor.execute(sql, [game_id, since])
    rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({'timestamp': row[0],
                       'player_id': row[1],
                       'event_type': row[2],
                       'data': parse_extra_data(row[3], row[2])})
    return result
