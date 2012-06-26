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

# Imports ###################################################################

from datetime import datetime, timedelta
from cardstories import event_log
from cardstories.game import CardstoriesGame

# Functions ##################################################################

playerid2name = {}

def get_all_players(cursor):
    '''
    Fetches all players from the django db. Returns a list of 3-element
    tuples containing id, email and name of each player in the django database.
    '''
    cursor.execute("SELECT id, username, first_name FROM auth_user")
    result = []
    for row in iter(cursor.next, None):
        id, email, name = row
        name = name and name.strip() or email.split('@')[0].strip()
        result.append((id, email, name,))
    return result

def get_unsubscribe_url(player_id):
    # TODO: Get URL from Django
    return 'http://cardstories.org/'

def seed_playerid2name(players_list):
    '''
    This function needs to be called in order to seed the playerid2game dict
    with data, so that get_player_name function can use it foor looking up player names.
    It expects a list of 3-element tuples, as returned by get_all_players().
    '''
    global playerid2name
    playerid2name = {}
    for id, _email, name in players_list:
        playerid2name[id] = name

def get_player_name(player_id, current_player_id=None):
    '''
    Returns player's name for player with id `player_id`.
    If the second parameter (`current_player_id`) equals the first one,
    it simply returns the string 'You', to make emails appear more friendly.
    '''
    if player_id == current_player_id:
        return 'You'
    else:
        return playerid2name[player_id]

def yesterday():
    'Helper function that returns a datetime of 24 hours ago.'
    return datetime.now() - timedelta(days=1)

def get_event_description(event, player_id):
    '''
    Helper function that returns a description of the `event` in a human
    friendly format. The description is meant to be put directly into the emails.
    '''
    player_name = lambda: get_player_name(event['player_id'], player_id)
    event_type = event['event_type']

    if event_type == event_log.GAME_CREATED:
        desc = '%s created the game' % player_name()
    elif event_type == event_log.OWNER_CHOSE_CARD:
        desc = '%s chose the card' % player_name()
    elif event_type == event_log.OWNER_WROTE_STORY:
        desc = '%s wrote the story' % player_name()
    elif event_type == event_log.GAME_MOVED_TO_VOTING:
        desc = 'The voting phase started'
    elif event_type == event_log.GAME_COMPLETED:
        desc = 'The game was completed'
    elif event_type == event_log.GAME_CANCELED:
        desc = 'The game was canceled'
    elif event_type == event_log.PLAYER_INVITED:
        invitee_name = get_player_name(event['data'], player_id)
        desc = '%s invited %s to join the game' % (player_name(), invitee_name)
    elif event_type == event_log.PLAYER_JOINED:
        desc = '%s joined the game' % player_name()
    elif event_type == event_log.PLAYER_LEFT:
        desc = '%s left the game' % player_name()
    elif event_type == event_log.PLAYER_PICKED_CARD:
        desc = '%s picked a fake card' % player_name()
    elif event_type == event_log.PLAYER_VOTED:
        desc = '%s voted' % player_name()

    return desc

def get_players_last_activity(cursor, player_id):
    '''
    Returns the time of player's last logged activity as a datetime object.
    '''
    last_activity = event_log.get_players_last_activity(cursor, player_id)
    if last_activity:
        return last_activity['timestamp']
    else:
        return None

def get_player_game_ids(cursor, player_id):
    '''
    Returns a list of ids of all games that the player has ever
    participated in, including the ones he created.
    '''
    cursor.execute("SELECT game_id FROM player2game WHERE player_id = ?", [player_id])
    rows = cursor.fetchall()
    game_ids = map(lambda row: row[0], rows)
    return game_ids

def get_game_activities(cursor, game_ids, player_id, happened_since=None):
    '''
    Takes a list of `game_ids` and returns a list of dicts corresponding
    to each game that had any events happen to it since `happened_since`,
    which defaults to 24 hours ago. The dict includes information for keys:
    'game_id', 'state', 'sentence', 'owner_name', and 'events'.
    The 'events' entry is a list of human readable event descriptions.
    '''
    if happened_since is None:
        happened_since = yesterday()
    result = []
    for game_id in game_ids:
        # Get game activity since `happened_since`.
        events = event_log.get_game_activities(cursor, game_id, happened_since)
        if len(events):
            cursor.execute("SELECT state, owner_id, sentence FROM games WHERE id = ?", [game_id])
            row = cursor.fetchone()
            if row:
                state, owner_id, sentence = row
                result.append({'game_id': game_id,
                               'state': state,
                               'sentence': sentence,
                               'owner_name': get_player_name(owner_id, player_id),
                               'events': map(lambda e: get_event_description(e, player_id), events)})
    return result

def get_available_games(cursor, created_since=None, exclude_game_ids=None):
    '''
    Returns a list of dict objects corresponding to games that are available to
    be played and were created since `created_since` which defaults to 24 hours ago.
    It optionally accepts a list of game_ids to exclude from the results.
    The returned dict objects contain information for keys:
    'game_id, 'owner_name', and 'sentence'.
    '''
    if created_since is None:
        created_since = yesterday()
    if exclude_game_ids is None:
        exclude_game_ids = []
    sql = """SELECT id, owner_id, sentence
               FROM games
             WHERE state = 'invitation'
               AND players < ?
               AND created > ?
               AND id NOT IN (%s)""" % ','.join([str(id) for id in exclude_game_ids])
    cursor.execute(sql, [CardstoriesGame.NPLAYERS, created_since])
    rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({'game_id': row[0],
                       'owner_name': get_player_name(row[1]),
                       'sentence': row[2]})
    return result

def get_completed_games(cursor, completed_since=None, exclude_game_ids=None):
    '''
    Returns a list of dict objects corresponding to games that have been completed
    since `completed_since` which defaults to 24 hours ago.
    It optionally accepts a list of game_ids to exclude from the results.
    The returned dict objects contain information for keys:
    'game_id, 'owner_name', and 'sentence'.
    '''
    if completed_since is None:
        completed_since = yesterday()
    if exclude_game_ids is None:
        exclude_game_ids = []
    sql = """SELECT id, owner_id, sentence
               FROM games
             WHERE state = 'complete'
               AND created > ?
               AND id NOT IN (%s)""" % ','.join([str(id) for id in exclude_game_ids])
    cursor.execute(sql, [completed_since])
    rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({'game_id': row[0],
                       'owner_name': get_player_name(row[1]),
                       'sentence': row[2]})
    return result
