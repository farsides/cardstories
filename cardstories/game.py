# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Loic Dachary <loic@dachary.org>
# Copyright (C) 2011-2012 Farsides <contact@farsides.com>
#
# Authors:
#          Loic Dachary <loic@dachary.org>
#          Xavier Antoviaque <xavier@antoviaque.org>
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
import random
from math import ceil

from twisted.internet import defer, reactor

from cardstories.poll import Pollable
from cardstories.exceptions import CardstoriesWarning

class CardstoriesGame(Pollable):

    MIN_PICKED = 3 # there needs to be at least 3 cards to move to the voting phase
    MIN_VOTED = 2 # there needs to be at least 2 votes to complete the game
    NCARDS = 43
    NPLAYERS = 6
    CARDS_PER_PLAYER = 7
    DEFAULT_COUNTDOWN_DURATION = 60 # needs to be coordinated with the value on the UI
    POINTS_GM_WON = 10
    POINTS_GM_LOST = 5
    POINTS_GM_FAILED = 2
    POINTS_P_WON = 5
    POINTS_P_LOST = 1
    POINTS_P_FAILED = 2
    LEVEL_A = 0.5
    LEVEL_B = 1.5
    LEVEL_C = 3.5

    def __init__(self, service, id=None):
        self.service = service
        self.settings = service.settings
        self.id = id
        self.owner_id = None
        self.players = []
        self.invited = []
        Pollable.__init__(self, self.settings.get('poll-timeout', 30))

    def touch(self, *args, **kwargs):
        self.update_timer()
        kwargs['game_id'] = [self.id]
        return Pollable.touch(self, kwargs)

    def destroy(self):
        self.clear_countdown()
        if hasattr(self, 'timer') and self.timer.active():
            self.timer.cancel()
        if hasattr(self, 'service'):
            del self.service
        return Pollable.destroy(self)

    def get_id(self):
        return self.id

    def get_owner_id(self):
        return self.owner_id

    def get_players(self):
        return self.players + self.invited

    def load(self, cursor):
        cursor.execute("SELECT player_id FROM player2game WHERE game_id = %d" % self.id)
        self.players += [ x[0] for x in cursor.fetchall() ]
        cursor.execute("SELECT player_id FROM invitations WHERE game_id = %d" % self.id)
        self.invited += [ x[0] for x in cursor.fetchall() ]
        cursor.execute("SELECT owner_id FROM games WHERE id = %d" % self.id)
        self.owner_id = cursor.fetchone()[0]
        self.update_timer()

    def update_timer(self):
        if hasattr(self, 'timer') and self.timer.active():
            self.timer.cancel()
        self.timer = reactor.callLater(self.settings.get('game-timeout', 24 * 60 * 60), self.state_change)

    STATE_CHANGE_TO_VOTE = 1
    STATE_CHANGE_TO_COMPLETE = 2
    STATE_CHANGE_CANCEL = 3

    @defer.inlineCallbacks
    def state_change(self):
        game, players_id_list = yield self.game(self.get_owner_id())
        if game['state'] == 'create':
            yield self.cancel()
            result = self.STATE_CHANGE_CANCEL
        elif game['state'] == 'invitation':
            if game['ready']:
                yield self.voting({ 'owner_id': [self.get_owner_id()],
                                    'game_id': [self.get_id()] })
                result = self.STATE_CHANGE_TO_VOTE
            else:
                yield self.cancel()
                result = self.STATE_CHANGE_CANCEL
        elif game['state'] == 'vote':
            if game['ready']:
                yield self.complete(self.get_owner_id())
                result = self.STATE_CHANGE_TO_COMPLETE
            else:
                yield self.cancel()
                result = self.STATE_CHANGE_CANCEL
        else:
            raise Exception, "Unexpected state: '%s'" % game['state']
        defer.returnValue(result)

    @defer.inlineCallbacks
    def cancel(self):
        yield self.service.db.runOperation("UPDATE games SET state = 'canceled' WHERE id = ?", [ self.get_id() ])
        yield self.cancelInvitations()
        self.destroy() # notify before altering the in core representation
        self.invited = []
        defer.returnValue({})

    def leaveInteraction(self, transaction, game_id, player_id):
        transaction.execute("DELETE FROM player2game WHERE player_id = ? AND game_id = ?", [ player_id, game_id ])
        deleted = transaction.rowcount > 0
        if deleted:
            transaction.execute("UPDATE games SET players = players - 1 WHERE id = ?", [ game_id ])
        return deleted

    @defer.inlineCallbacks
    def leave_api(self, args):
        self.service.required(args, 'leave', 'player_id')
        player_ids = args['player_id']
        deleted = yield self.leave(player_ids)
        yield self.touch()
        defer.returnValue({'deleted': deleted})

    @defer.inlineCallbacks
    def leave(self, player_ids):
        deleted = 0
        for player_id in player_ids:
            self.players.remove(int(player_id))
            count = yield self.service.db.runInteraction(self.leaveInteraction, self.get_id(), int(player_id))
            deleted += count
        defer.returnValue(deleted)

    def playerInteraction(self, transaction, player_id):
        transaction.execute("SELECT player_id, score, score_prev, levelups from players WHERE player_id = ?", [player_id])
        rows = transaction.fetchall()
        if not rows:
            transaction.execute("INSERT INTO players (player_id, score, score_prev, levelups) VALUES (?, ?, ?, ?)", [player_id, 0, 0, 0])

    def createInteraction(self, transaction, owner_id):
        transaction.execute("INSERT INTO games (owner_id, cards, board, created) VALUES (?, '', '', datetime('now'))", [owner_id])
        game_id = transaction.lastrowid
        transaction.execute("INSERT INTO player2game (game_id, player_id, cards) VALUES (?, ?, '')", [ game_id, owner_id ])
        return game_id

    @defer.inlineCallbacks
    def create(self, owner_id):
        self.owner_id = owner_id
        game_id = yield self.service.db.runInteraction(self.createInteraction, self.owner_id)
        yield self.service.db.runInteraction(self.playerInteraction, self.owner_id)
        self.id = game_id
        self.players.append(self.owner_id)
        self.update_timer()
        defer.returnValue(game_id)

    def setCardInteraction(self, transaction, game_id, player_id, card):
        transaction.execute("SELECT state, owner_id FROM games WHERE id = ?", [ game_id ])
        state, owner_id = transaction.fetchone()
        if player_id != owner_id:
            raise Exception, 'Only game owner can set the card.'
        if state != 'create':
            raise CardstoriesWarning('WRONG_STATE_FOR_SETTING_CARD', {'game_id': game_id, 'state': state})
        transaction.execute("UPDATE player2game SET picked = ?, cards = ? WHERE game_id = ? AND player_id = ?", [ card, card, game_id, player_id ])
        # Generate a random set of cards (without the chosen card).
        cards = [ chr(x) for x in range(1, self.NCARDS + 1) ]
        cards.remove(card)
        random.shuffle(cards)
        cards = ''.join(cards)
        # Update cards for all the players who have already joined the game.
        transaction.execute("SELECT player_id from player2game WHERE game_id = ? AND player_id != ?", [ game_id, owner_id])
        rows = transaction.fetchall()
        for row in rows:
            player_cards = cards[:self.CARDS_PER_PLAYER]
            cards = cards[self.CARDS_PER_PLAYER:]
            transaction.execute("UPDATE player2game SET cards = ? WHERE game_id = ? AND player_id = ?", [ player_cards, game_id, row[0] ])
        # Finally, update the available cards on the game, left after dealing
        # each player his set.
        transaction.execute("UPDATE games SET cards = ?, board = ? WHERE id = ?", [ cards, card, game_id ])

    @defer.inlineCallbacks
    def set_card(self, player_id, card):
        yield self.service.db.runInteraction(self.setCardInteraction, self.get_id(), player_id, chr(card))
        result = yield self.touch(type='set_card', player_id=player_id, card=card)
        defer.returnValue(result)

    def setSentenceInteraction(self, transaction, player_id, game_id, sentence):
        transaction.execute("SELECT state, owner_id FROM games WHERE id = ?", [ game_id ])
        state, owner_id = transaction.fetchone()
        if owner_id != player_id:
            raise Exception, "Only game owner can set the sentence."
        if state != 'create':
            raise CardstoriesWarning('WRONG_STATE_FOR_SETTING_SENTENCE', {'game_id': game_id, 'state': state})
        transaction.execute("SELECT cards FROM player2game WHERE game_id = %d AND player_id = %d" % (game_id, player_id))
        card = transaction.fetchone()[0]
        if not card:
            raise CardstoriesWarning('CARD_NOT_SET', {'game_id': game_id })
        transaction.execute("UPDATE games SET sentence = ?, state = 'invitation' WHERE id = ?", [ sentence, game_id ])

    @defer.inlineCallbacks
    def set_sentence(self, player_id, sentence):
        yield self.service.db.runInteraction(self.setSentenceInteraction, player_id, self.id, sentence)
        result = yield self.touch(type='set_sentence', sentence=sentence)
        defer.returnValue(result)

    def calculate_level(self, score):
        # Players start with score 0 at level 1, and by convention only
        # need one point to reach level 2.
        if not score or score < 0:
            level = 1 
            score_next = 1
            score_left = 1

        # Starting at level 2, levels are defined by a "points to the
        # next level" formula, tunable using 3 constants.  Precisely
        # due to this tunable nature, levels are not stored on the
        # database, but calculated whenever a request is made.
        else:
            to_next = lambda l: int(ceil(self.LEVEL_A * l ** 3 + \
                                         self.LEVEL_B * l ** 2 + \
                                         self.LEVEL_C * l))
            level = 2
            remainder = score - 1
            score_next = to_next(level)
            while remainder >= score_next:
                remainder -= score_next
                level += 1
                score_next = to_next(level)

            score_left = score_next - remainder

        return level, score_next, score_left

    @defer.inlineCallbacks
    def game(self, player_id):
        db = self.service.db
        game_id = self.get_id()
        rows = yield db.runQuery("SELECT owner_id, sentence, cards, board, state FROM games WHERE id = ?", [ game_id ])
        if not rows:
            raise CardstoriesWarning('GAME_DOES_NOT_EXIST', {'game_id': game_id, 'player_id': player_id})
        (owner_id, sentence, cards, board, state) = rows[0]
        if owner_id == player_id:
            cards = [ ord(c) for c in cards ]
            invited = list(self.invited)
        else:
            cards = None
            invited = None
        if owner_id != player_id and state in ('create', 'invitation'):
            board = None
        else:
            board = [ ord(c) for c in board ]
        sql = ("SELECT "
               "player2game.player_id, "
               "player2game.cards, "
               "player2game.picked, "
               "player2game.vote, "
               "player2game.win, "
               "players.score, "
               "players.score_prev, "
               "players.levelups "
               "FROM player2game LEFT JOIN players "
               "ON player2game.player_id = players.player_id "
               "WHERE game_id = ? ORDER BY serial")
        rows = yield db.runQuery(sql, [ game_id ])
        picked_count = 0
        voted_count = 0
        players = []
        winner_card = None
        myself = None
        players_id_list = [] # Keep track of all players being referenced
        for player in rows:
            # player_id
            players_id_list.append(player[0])

            # player_cards
            if player[0] == player_id or owner_id == player_id:
                player_cards = [ ord(c) for c in player[1] ]
            else:
                player_cards = None

            # picked
            if player[2] != None:
                if (state == 'complete' or player[0] == player_id or owner_id == player_id):
                    picked = ord(player[2])
                else:
                    picked = ''
            else:
                picked = None
            if player[2] != None:
                picked_count += 1

            # self
            if player[0] == player_id:
                myself = [ self.ord(player[2]), self.ord(player[3]), player_cards ]

            # vote / winner_card
            if state == 'complete' or owner_id == player_id:
                if player[0] == owner_id and player[2]:
                    winner_card = ord(player[2])
                vote = self.ord(player[3])
            else:
                if player[0] == owner_id and player[2]:
                    winner_card = ''
                if player[3] != None:
                    vote = ''
                else:
                    vote = None
            if player[3] != None:
                voted_count += 1

            # win
            win = player[4]

            # Set score and level, but only for the requesting player.
            if player[0] == player_id:
                score = player[5]
                score_prev = player[6]
                level, score_next, score_left = self.calculate_level(score)
                level_prev, _, _ = self.calculate_level(score_prev)
            else:
                score = None
                level = None
                score_next = None
                score_left = None
                score_prev = None
                level_prev = None

            # players
            players.append({'id': player[0],
                            'cards': player_cards,
                            'picked': picked,
                            'vote': vote,
                            'win': win,
                            'score': score,
                            'level': level,
                            'score_next': score_next,
                            'score_left': score_left,
                            'score_prev': score_prev,
                            'level_prev': level_prev})

        ready = None
        if state == 'invitation':
            ready = picked_count >= self.MIN_PICKED
        elif state == 'vote':
            ready = voted_count >= self.MIN_VOTED
        defer.returnValue([{'id': game_id,
                            'modified': self.get_modified(),
                            'sentence': sentence,
                            'winner_card': winner_card,
                            'cards': cards,
                            'board': board,
                            'state': state,
                            'ready': ready,
                            'countdown_finish': self.get_countdown_finish(),
                            'self': myself,
                            'owner': owner_id == player_id,
                            'owner_id': owner_id,
                            'players': players,
                            'invited': invited },
                            players_id_list])

    def participateInteraction(self, transaction, game_id, player_id):
        transaction.execute("SELECT players, cards FROM games WHERE id = %d" % game_id)
        (players, cards) = transaction.fetchall()[0]
        no_room = CardstoriesWarning('GAME_FULL', {'game_id': game_id, 'player_id': player_id, 'max_players': self.NPLAYERS})
        if players >= self.NPLAYERS:
            raise no_room
        transaction.execute("UPDATE games SET cards = ?, players = players + 1 WHERE id = %d AND players = %d" % (game_id, players), [ cards[self.CARDS_PER_PLAYER:] ])
        if transaction.rowcount == 0:
            raise no_room
        transaction.execute("INSERT INTO player2game (game_id, player_id, cards) VALUES (?, ?, ?)", [ game_id, player_id, cards[:self.CARDS_PER_PLAYER] ])
        transaction.execute("DELETE FROM invitations WHERE game_id = ? AND player_id = ?", [ game_id, player_id ])

    @defer.inlineCallbacks
    def participate(self, player_id):
        yield self.service.db.runInteraction(self.participateInteraction, self.get_id(), player_id)
        yield self.service.db.runInteraction(self.playerInteraction, player_id)
        if player_id in self.invited:
            self.invited.remove(player_id)
        self.players.append(player_id)
        result = yield self.touch(type='participate', player_id=player_id)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def voting(self, owner_id):
        self.clear_countdown()
        game, players_id_list = yield self.game(self.get_owner_id())
        discarded = []
        board = []
        for player in game['players']:
            if player['picked'] == None:
                discarded.append(player['id'])
            else:
                board.append(player['picked'])
        random.shuffle(board)
        yield self.leave(discarded)
        board = ''.join([chr(card) for card in board])
        yield self.service.db.runOperation("UPDATE games SET board = ?, state = 'vote' WHERE id = ?", [ board, self.get_id() ])
        yield self.cancelInvitations()
        self.invited = []
        result = yield self.touch(type='voting')
        defer.returnValue(result)

    @defer.inlineCallbacks
    def player2game(self, player_id):
        rows = yield self.service.db.runQuery("SELECT cards, picked, vote, win FROM player2game WHERE game_id = %d AND player_id = %d" % (self.get_id(), player_id))
        defer.returnValue({ 'cards': map(lambda c: ord(c), rows[0][0]),
                            'picked': self.ord(rows[0][2]),
                            'vote': self.ord(rows[0][2]),
                            'win': rows[0][3] })

    def is_countdown_active(self):
        return hasattr(self, 'countdown_timer') and self.countdown_timer.active()

    def get_countdown_duration(self):
        custom_duration = hasattr(self, 'countdown_duration') and self.countdown_duration
        return custom_duration or self.DEFAULT_COUNTDOWN_DURATION

    def set_countdown_duration(self, duration):
        self.countdown_duration = duration

    def get_countdown_finish(self):
        if self.is_countdown_active():
            return int(round(self.countdown_timer.getTime() * 1000))

    def start_countdown(self):
        duration = self.get_countdown_duration()
        self.countdown_timer = reactor.callLater(duration, self.state_change)

    def reset_countdown(self):
        self.countdown_timer.cancel()
        self.start_countdown()

    def clear_countdown(self):
        if hasattr(self, 'countdown_duration'):
            del self.countdown_duration
        if self.is_countdown_active():
            self.countdown_timer.cancel()

    @defer.inlineCallbacks
    def set_countdown(self, duration):
        self.set_countdown_duration(duration)
        if self.is_countdown_active():
            self.reset_countdown()
        result = yield self.touch(type='set_countdown')
        defer.returnValue(result)

    def pickInteraction(self, transaction, game_id, player_id, card):
        transaction.execute("SELECT state, owner_id FROM games WHERE id = ?", [ game_id ])
        state, owner_id = transaction.fetchone()
        if state == 'invitation':
            transaction.execute("UPDATE player2game SET picked = ? WHERE game_id = ? AND player_id = ?", [ chr(card), game_id, player_id ])
        else:
            raise CardstoriesWarning('WRONG_STATE_FOR_PICKING', {'game_id': game_id, 'player_id': player_id, 'state': state})

    @defer.inlineCallbacks
    def pick(self, player_id, card):
        yield self.service.db.runInteraction(self.pickInteraction, self.get_id(), player_id, card)
        count = yield self.service.db.runQuery("SELECT COUNT(*) FROM player2game WHERE game_id = ? AND picked IS NOT NULL", [ self.get_id() ])
        if count[0][0] >= self.MIN_PICKED and not self.is_countdown_active():
            self.start_countdown()
        result = yield self.touch(type='pick', player_id=player_id, card=card)
        defer.returnValue(result)

    def voteInteraction(self, transaction, game_id, player_id, vote):
        transaction.execute("SELECT state FROM games WHERE id = ?", [ game_id ])
        state = transaction.fetchone()[0]
        if state == 'vote':
            transaction.execute("UPDATE player2game SET vote = ? WHERE game_id = ? AND player_id = ?", [ chr(vote), game_id, player_id ])
        else:
            raise CardstoriesWarning('WRONG_STATE_FOR_VOTING', {'game_id': game_id, 'player_id': player_id, 'state': state})

    @defer.inlineCallbacks
    def vote(self, player_id, vote):
        yield self.service.db.runInteraction(self.voteInteraction, self.get_id(), player_id, vote)
        count = yield self.service.db.runQuery("SELECT COUNT(*) FROM player2game WHERE game_id = ? AND vote IS NOT NULL", [ self.get_id() ])
        if count[0][0] >= self.MIN_VOTED and not self.is_countdown_active():
            self.start_countdown()
        result = yield self.touch(type='vote', player_id=player_id, vote=vote)
        defer.returnValue(result)

    def completeInteraction(self, transaction, game_id, owner_id):
        transaction.execute("SELECT cards FROM player2game WHERE game_id = %d AND player_id = %d" % (game_id, owner_id))
        winner_card = transaction.fetchone()[0]
        transaction.execute("SELECT vote, picked, player_id FROM player2game WHERE game_id = %d AND player_id != %d AND vote IS NOT NULL" % (game_id, owner_id))
        players_count = 0
        guessed = []
        failed = []
        score = {}
        player2vote = {}
        pick2player = {}
        for (vote, picked, player_id) in transaction.fetchall():
            players_count += 1
            player2vote[player_id] = vote
            pick2player[picked] = player_id
            if vote == winner_card:
                guessed.append(player_id)
            else:
                failed.append(player_id)

        if len(guessed) > 0 and len(guessed) < players_count:
            winners = guessed + [ owner_id ]
            score[owner_id] = self.POINTS_GM_WON
            for player_id in guessed:
                score[player_id] = self.POINTS_P_WON
            for player_id in failed:
                score[owner_id] += self.POINTS_GM_FAILED
                score[player_id] = self.POINTS_P_LOST
        else:
            winners = failed + guessed
            score[owner_id] = self.POINTS_GM_LOST
            for player_id in winners:
                score[player_id] = self.POINTS_P_WON

        # Also distribute points to players who fooled other players.
        for player_id in failed:
            vote = player2vote[player_id]
            try:
                candidate = pick2player[vote]
                try:
                    score[candidate] += self.POINTS_P_FAILED
                except KeyError:
                    score[candidate] = self.POINTS_P_FAILED
            except KeyError:
                pass

        transaction.execute("UPDATE player2game SET win = 'y' WHERE "
                            "  game_id = %d AND " % game_id +
                            "  player_id IN ( %s ) " % ','.join([ str(id) for id in winners ]))
        transaction.execute("UPDATE games SET completed = datetime('now'), state = 'complete' WHERE id = %d" % game_id)

        # Update scores in the database.
        for player_id in score.keys():
            transaction.execute("UPDATE players SET score_prev = score, score = score + %d WHERE player_id = %s" % (score[player_id], player_id))

    @defer.inlineCallbacks
    def complete(self, owner_id):
        self.clear_countdown()
        game, players_id_list = yield self.game(self.get_owner_id())
        yield self.service.db.runInteraction(self.completeInteraction, self.get_id(), owner_id)
        result = yield self.touch(type='complete')
        self.destroy()
        defer.returnValue(result)

    def cancelInvitations(self):
        return self.service.db.runQuery("DELETE FROM invitations WHERE game_id = ?", [ self.get_id() ])

    @defer.inlineCallbacks
    def invite(self, player_ids):
        invited = []
        for player_id in player_ids:
            if player_id not in self.invited:
                invited.append(player_id)
                yield self.service.db.runQuery("INSERT INTO invitations (player_id, game_id) VALUES (?, ?)", [ player_id, self.get_id() ])
        self.invited += invited
        result = yield self.touch(type='invite', invited=invited)
        defer.returnValue(result)

    @staticmethod
    def ord(c):
        if c:
            return ord(c)
        else:
            return c
