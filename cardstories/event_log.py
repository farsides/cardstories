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

from twisted.enterprise import adbapi
from twisted.internet import defer


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

