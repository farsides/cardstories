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

from twisted.python import runtime
from twisted.internet import defer, reactor

from cardstories.poll import pollable

class CardstoriesGame(pollable):

    MIN_PICKED = 3 # there needs to be at least 3 cards to move to the voting phase
    NCARDS = 36
    NPLAYERS = 6
    CARDS_PER_PLAYER = 7

    def __init__(self, service, id = None):
        self.service = service
        self.settings = service.settings
        self.id = id
        self.players = []
        self.invited = []
        pollable.__init__(self, self.settings.get('poll-timeout', 300))

    def touch(self):
        return pollable.touch(self, {'game_id': [self.id]})

    def get_id(self):
        return self.id

    def get_players(self):
        return self.players + self.invited

    def load(self, cursor):
        cursor.execute("SELECT player_id FROM player2game WHERE game_id = %d" % self.id)
        self.players += [ x[0] for x in cursor.fetchall() ]
        cursor.execute("SELECT player_id FROM invitations WHERE game_id = %d" % self.id)
        self.invited += [ x[0] for x in cursor.fetchall() ]

    def createInteraction(self, transaction, card, sentence, owner_id):
        cards = [ chr(x) for x in range(1, self.NCARDS + 1) ]
        cards.remove(card)
        random.shuffle(cards)
        transaction.execute("INSERT INTO games (sentence, cards, board, owner_id, created) VALUES (?, ?, ?, ?, datetime('now'))", [sentence, ''.join(cards), card, owner_id])
        game_id = transaction.lastrowid
        transaction.execute("INSERT INTO player2game (game_id, player_id, cards, picked) VALUES (?, ?, ?, ?)", [ game_id, owner_id, card, card ])
        return game_id

    @defer.inlineCallbacks
    def create(self, args):
        self.service.required(args, 'create', 'card', 'sentence', 'owner_id')
        card = chr(int(args['card'][0]))
        sentence = args['sentence'][0]
        owner_id = int(args['owner_id'][0])
        game_id = yield self.service.db.runInteraction(self.createInteraction, card, sentence, owner_id)
        self.id = game_id
        self.players.append(owner_id)
        defer.returnValue({'game_id': game_id})

    @defer.inlineCallbacks
    def game(self, args):
        self.service.required(args, 'game', 'game_id')
        game_id = int(args['game_id'][0])
        if args.has_key('player_id'):
            player_id = int(args['player_id'][0])
        else:
            player_id = None
        rows = yield self.service.db.runQuery("SELECT owner_id, sentence, cards, board, state, created, completed FROM games WHERE id = ?", [game_id])
        ( owner_id, sentence, cards, board, state, created, completed ) = rows[0]
        if owner_id == player_id:
            cards = [ ord(c) for c in cards ]
        else:
            cards = None
        if owner_id != player_id and state == 'invitation':
            board = None
        else:
            board = [ ord(c) for c in board ]
        rows = yield self.service.db.runQuery("SELECT player_id, cards, picked, vote, win FROM player2game WHERE game_id = ? ORDER BY player_id", [ game_id ])
        picked_count = 0
        vote_count = 0
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
                vote_count += 1
            players.append([ player[0], vote, player[4], picked, player_cards ])
        ready = None
        if state == 'invitation':
            ready = picked_count >= self.MIN_PICKED
        elif state == 'vote':
            ready = picked_count == vote_count + 1 # + 1 is because the owner does not get to vote
        defer.returnValue({ 'id': game_id,
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
    def participate(self, args):
        self.service.required(args, 'participate', 'player_id', 'game_id')
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        yield self.service.db.runInteraction(self.participateInteraction, game_id, player_id)
        if player_id in self.invited:
            self.invited.remove(player_id)
        self.players.append(player_id)
        defer.returnValue(self.touch())

    @defer.inlineCallbacks
    def voting(self, args):
        self.service.required(args, 'voting', 'owner_id', 'game_id')
        game_id = int(args['game_id'][0])
        owner_id = int(args['owner_id'][0])
        rows = yield self.service.db.runQuery("SELECT picked FROM player2game WHERE game_id = %d AND picked IS NOT NULL ORDER BY picked" % game_id)
        board = ''.join(card for (card,) in rows)
        yield self.service.db.runOperation("UPDATE games SET board = ?, state = 'vote' WHERE id = %d AND owner_id = %d" % ( game_id, owner_id ), [ board ])
        yield self.cancelInvitations(game_id)
        defer.returnValue(self.touch())

    @defer.inlineCallbacks
    def player2game(self, args):
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        rows = yield self.service.db.runQuery("SELECT cards, picked, vote, win FROM player2game WHERE game_id = %d AND player_id = %d" % ( game_id, player_id ))
        defer.returnValue({ 'cards': map(lambda c: ord(c), rows[0][0]),
                            'picked': self.ord(rows[0][2]),
                            'vote': self.ord(rows[0][2]),
                            'win': rows[0][3] })

    @defer.inlineCallbacks
    def pick(self, args):
        self.service.required(args, 'pick', 'player_id', 'game_id', 'card')
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        card = int(args['card'][0])
        yield self.service.db.runOperation("UPDATE player2game SET picked = ? WHERE game_id = %d AND player_id = %d" % ( game_id, player_id ), [ chr(card) ])
        defer.returnValue(self.touch())

    @defer.inlineCallbacks
    def vote(self, args):
        self.service.required(args, 'vote', 'player_id', 'game_id', 'card')
        player_id = int(args['player_id'][0])
        game_id = int(args['game_id'][0])
        vote = int(args['card'][0])
        yield self.service.db.runOperation("UPDATE player2game SET vote = ? WHERE game_id = %d AND player_id = %d" % ( game_id, player_id ), [ chr(vote) ])
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
    def complete(self, args):
        self.service.required(args, 'complete', 'owner_id', 'game_id')
        owner_id = int(args['owner_id'][0])
        game_id = int(args['game_id'][0])
        yield self.service.db.runInteraction(self.completeInteraction, game_id, owner_id)
        defer.returnValue(self.touch())

    def cancelInvitations(self, game_id):
        self.invited = []
        return self.service.db.runQuery("DELETE FROM invitations WHERE game_id = ?", [ game_id ])

    @defer.inlineCallbacks
    def invite(self, args):
        self.service.required(args, 'invite', 'owner_id', 'player_id', 'game_id')
        game_id = args['game_id'][0]
        for player_id in args['player_id']:
            yield self.service.db.runQuery("INSERT INTO invitations (player_id, game_id) VALUES (?, ?)", [ player_id, game_id ])
        self.invited += args['player_id']
        defer.returnValue(self.touch())

    @staticmethod
    def ord(c):
        if c:
            return ord(c)
        else:
            return c


