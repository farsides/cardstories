#
# Copyright (C) 2011 Dachary <loic@dachary.org>
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

from twisted.python import runtime, log
from twisted.internet import defer, reactor

from cardstories.poll import pollable

class CardstoriesGame(pollable):

    MIN_PICKED = 3 # there needs to be at least 3 cards to move to the voting phase
    MIN_VOTED = 2 # there needs to be at least 2 votes to complete the game
    NCARDS = 36
    NPLAYERS = 6
    CARDS_PER_PLAYER = 7

    def __init__(self, service, id = None):
        self.service = service
        self.settings = service.settings
        self.id = id
        self.owner_id = None
        self.players = []
        self.invited = []
        pollable.__init__(self, self.settings.get('poll-timeout', 300))

    def touch(self):
        self.update_timer()
        return pollable.touch(self, {'game_id': [self.id]})

    def destroy(self):
        if hasattr(self, 'timer') and self.timer.active():
            self.timer.cancel()
        if hasattr(self, 'service'):
            del self.service
        return pollable.destroy(self)

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

    STATE_CHANGE_TO_VOTE     = 1
    STATE_CHANGE_TO_COMPLETE = 2
    STATE_CHANGE_CANCEL      = 3

    @defer.inlineCallbacks
    def state_change(self):
        game = yield self.game(self.get_owner_id())
        if game['state'] == 'invitation':
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
            raise UserWarning('unexpected state %s' % game.state)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def cancel(self):
        yield self.service.db.runOperation("UPDATE games SET state = 'canceled' WHERE id = ?", [ self.get_id() ])
        yield self.cancelInvitations()
        yield self.service.db.runOperation("DELETE FROM player2game WHERE game_id = ?", [ self.get_id() ])
        self.destroy() # notify before altering the in core representation
        self.invited = []
        self.players = []
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
        self.touch()
        defer.returnValue({'deleted': deleted})

    @defer.inlineCallbacks
    def leave(self, player_ids):
        deleted = 0
        for player_id in player_ids:
            self.players.remove(int(player_id))
            count = yield self.service.db.runInteraction(self.leaveInteraction, self.get_id(), int(player_id))
            deleted += count
        defer.returnValue(deleted)

    def createInteraction(self, transaction, card, sentence, owner_id):
        cards = [ chr(x) for x in range(1, self.NCARDS + 1) ]
        cards.remove(card)
        random.shuffle(cards)
        transaction.execute("INSERT INTO games (sentence, cards, board, owner_id, created) VALUES (?, ?, ?, ?, datetime('now'))", [sentence, ''.join(cards), card, owner_id])
        game_id = transaction.lastrowid
        transaction.execute("INSERT INTO player2game (game_id, player_id, cards, picked) VALUES (?, ?, ?, ?)", [ game_id, owner_id, card, card ])
        return game_id

    @defer.inlineCallbacks
    def create(self, card, sentence, owner_id):
        self.owner_id = owner_id
        game_id = yield self.service.db.runInteraction(self.createInteraction, chr(card), sentence, self.owner_id)
        self.id = game_id
        self.players.append(self.owner_id)
        self.update_timer()
        defer.returnValue(game_id)

    @defer.inlineCallbacks
    def game(self, player_id):
        rows = yield self.service.db.runQuery("SELECT owner_id, sentence, cards, board, state FROM games WHERE id = ?", [self.get_id()])
        ( owner_id, sentence, cards, board, state ) = rows[0]
        if owner_id == player_id:
            cards = [ ord(c) for c in cards ]
        else:
            cards = None
        if owner_id != player_id and state == 'invitation':
            board = None
        else:
            board = [ ord(c) for c in board ]
        rows = yield self.service.db.runQuery("SELECT player_id, cards, picked, vote, win FROM player2game WHERE game_id = ? ORDER BY player_id", [ self.get_id() ])
        picked_count = 0
        voted_count = 0
        players = []
        winner_card = None
        myself = None
        for player in rows:
            if player[0] == player_id or owner_id == player_id:
                player_cards = [ ord(c) for c in player[1] ]
            else:
                player_cards = None
            if player[2] != None and ( state == 'complete' or player[0] == player_id or owner_id == player_id ):
                picked = ord(player[2])
            else:
                picked = None
            if player[2] != None:
                picked_count += 1
            if player[0] == player_id:
                myself = [ self.ord(player[2]), self.ord(player[3]), player_cards ]
            if state == 'complete' or owner_id == player_id:
                if player[0] == owner_id:
                    winner_card = ord(player[1][0])
                vote = self.ord(player[3])
            else:
                vote = None
            if player[3] != None:
                voted_count += 1
            players.append([ player[0], vote, player[4], picked, player_cards ])
        ready = None
        if state == 'invitation':
            ready = picked_count >= self.MIN_PICKED
        elif state == 'vote':
            ready = voted_count >= self.MIN_VOTED
        defer.returnValue({ 'id': self.get_id(),
                            'modified': self.get_modified(),
                            'sentence': sentence,
                            'winner_card': winner_card,
                            'cards': cards, 
                            'board': board, 
                            'state': state,
                            'ready': ready,
                            'self': myself,
                            'owner': owner_id == player_id,
                            'players': players })

    def participateInteraction(self, transaction, game_id, player_id):
        transaction.execute("SELECT players, cards FROM games WHERE id = %d" % game_id)
        ( players, cards ) = transaction.fetchall()[0]
        no_room = UserWarning('player %d cannot join game %d because the %d players limit is reached' % ( player_id, game_id, self.NPLAYERS ))
        if players >= self.NPLAYERS:
            raise no_room
        transaction.execute("UPDATE games SET cards = ?, players = players + 1 WHERE id = %d AND players = %d" % ( game_id, players ), [ cards[self.CARDS_PER_PLAYER:] ])
        if transaction.rowcount == 0:
            raise no_room
        transaction.execute("INSERT INTO player2game (game_id, player_id, cards) VALUES (?, ?, ?)", [ game_id, player_id, cards[:self.CARDS_PER_PLAYER] ])
        transaction.execute("DELETE FROM invitations WHERE game_id = ? AND player_id = ?", [ game_id, player_id ])

    @defer.inlineCallbacks
    def participate(self, player_id):
        yield self.service.db.runInteraction(self.participateInteraction, self.get_id(), player_id)
        if player_id in self.invited:
            self.invited.remove(player_id)
        self.players.append(player_id)
        defer.returnValue(self.touch())

    @defer.inlineCallbacks
    def voting(self, owner_id):
        game = yield self.game(self.get_owner_id())
        discarded = []
        board = []
        for player in game['players']:
            if player[3] == None:
                discarded.append(player[0])
            else:
                board.append(player[3])
        random.shuffle(board)
        yield self.leave(discarded)
        board = ''.join([chr(card) for card in board])
        yield self.service.db.runOperation("UPDATE games SET board = ?, state = 'vote' WHERE id = ?", [ board, self.get_id() ])
        yield self.cancelInvitations()
        self.invited = []
        defer.returnValue(self.touch())

    @defer.inlineCallbacks
    def player2game(self, player_id):
        rows = yield self.service.db.runQuery("SELECT cards, picked, vote, win FROM player2game WHERE game_id = %d AND player_id = %d" % ( self.get_id(), player_id ))
        defer.returnValue({ 'cards': map(lambda c: ord(c), rows[0][0]),
                            'picked': self.ord(rows[0][2]),
                            'vote': self.ord(rows[0][2]),
                            'win': rows[0][3] })

    @defer.inlineCallbacks
    def pick(self, player_id, card):
        yield self.service.db.runOperation("UPDATE player2game SET picked = ? WHERE game_id = ? AND player_id = ?", [ chr(card), self.get_id(), player_id ])
        defer.returnValue(self.touch())

    @defer.inlineCallbacks
    def vote(self, player_id, vote):
        yield self.service.db.runOperation("UPDATE player2game SET vote = ? WHERE game_id = ? AND player_id = ?", [ chr(vote), self.get_id(), player_id ])
        defer.returnValue(self.touch())

    def completeInteraction(self, transaction, game_id, owner_id):
        transaction.execute("SELECT cards FROM player2game WHERE game_id = %d AND player_id = %d" % ( game_id, owner_id ))
        winner_card = transaction.fetchone()[0]
        transaction.execute("SELECT vote, player_id FROM player2game WHERE game_id = %d AND player_id != %d AND vote IS NOT NULL" % ( game_id, owner_id ))
        players_count = 0
        guessed = []
        failed = []
        for ( vote, player_id ) in transaction.fetchall():
            players_count += 1
            if vote == winner_card:
                guessed.append(player_id)
            else:
                failed.append(player_id)
        if len(guessed) > 0 and len(guessed) < players_count:
            winners = guessed + [ owner_id ]
        else:
            winners = failed + guessed
        transaction.execute("UPDATE player2game SET win = 'y' WHERE "
                            "  game_id = %d AND " % game_id + 
                            "  player_id IN ( %s ) " % ','.join([ str(id) for id in winners ]))
        transaction.execute("UPDATE games SET completed = datetime('now'), state = 'complete' WHERE id = %d" % game_id)

    @defer.inlineCallbacks
    def complete(self, owner_id):
        game = yield self.game(self.get_owner_id())
        no_vote = filter(lambda player: player[1] == None and player[0] != self.get_owner_id(), game['players'])
        yield self.leave([ player[0] for player in no_vote ])
        yield self.service.db.runInteraction(self.completeInteraction, self.get_id(), owner_id)
        defer.returnValue(self.touch())

    def cancelInvitations(self):
        return self.service.db.runQuery("DELETE FROM invitations WHERE game_id = ?", [ self.get_id() ])

    @defer.inlineCallbacks
    def invite(self, player_ids):
        for player_id in player_ids:
            yield self.service.db.runQuery("INSERT INTO invitations (player_id, game_id) VALUES (?, ?)", [ player_id, self.get_id() ])
        self.invited += player_ids
        defer.returnValue(self.touch())

    @staticmethod
    def ord(c):
        if c:
            return ord(c)
        else:
            return c


