#
# Copyright (C) 2011 Loic Dachary <loic@dachary.org>
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
import os

from twisted.python import log
from twisted.internet import reactor, defer

from cardstories.game import CardstoriesGame

class Plugin:

    def __init__(self, service):
        self.service = service
        self.id2info = {}
        self.handle(None)

    def name(self):
        return 'solo'

    def handle(self, event):
        if event == None:
            pass
        elif event['type'] == 'change':
            if self.id2info.has_key(event['game'].id):
                game = event['game']
                info = self.id2info[game.id]
                details = event['details']
                if details['type'] == 'pick' and details['player_id'] == info['player_id']:
                    def voting():
                        return game.voting(info['owner_id'])
                    reactor.callLater(0.01, voting)
                elif details['type'] == 'vote' and details['player_id'] == info['player_id']:
                    @defer.inlineCallbacks
                    def complete():
                        yield game.complete(info['owner_id'])
                        del self.id2info[game.id]
                    reactor.callLater(0.01, complete)

        self.service.listen().addCallback(self.handle)
        return defer.succeed(None)

    def copy(self, transaction, player_to, max_count):
        # 
        # get the id of a completed game at random
        #
        count = max_count
        while True:
            count -= 1
            transaction.execute("SELECT id, owner_id, board FROM games WHERE state = 'complete' ORDER BY RANDOM() LIMIT 1")
            ( game_from, owner_id, board ) = transaction.fetchall()[0]
            transaction.execute("SELECT count(*) FROM player2game WHERE game_id = ? AND player_id = ?", [ game_from, player_to ])
            if transaction.fetchone()[0] == 0:
                break
            elif count <= 0:
                return False
        #
        # copy the game
        #
        transaction.execute("INSERT INTO games (owner_id, players, sentence, cards, board, created) SELECT owner_id, players, sentence, cards, board, DATETIME('NOW') FROM games WHERE id = ?", [ game_from ])
        game_to = transaction.lastrowid
        #
        # copy the players
        #
        transaction.execute("INSERT INTO player2game (player_id, game_id, cards, picked, vote) SELECT player_id, ?, cards, picked, vote FROM player2game WHERE game_id = ?", [ game_to, game_from ])
        #
        # select a player at random
        #
        transaction.execute("SELECT player_id FROM player2game WHERE game_id = ? AND player_id != ? ORDER BY RANDOM() LIMIT 1", [ game_to, owner_id ])
        ( player_from, ) = transaction.fetchall()[0]
        #
        # replace the selected player with the player willing to play solo
        #
        transaction.execute("UPDATE player2game SET player_id = ?, picked = NULL, vote = NULL WHERE game_id = ? AND player_id = ? ", [ player_to, game_to, player_from ])
        return { 'game_id': game_to,
                 'owner_id': owner_id,
                 'player_id': player_to }
        
    @defer.inlineCallbacks
    def preprocess(self, result, request):
        if request.args.has_key('action') and request.args['action'][0] == 'solo':
            del request.args['action']
            player_id = request.args['player_id'][0]
            max_count = 5
            info = yield self.service.db.runInteraction(self.copy, player_id, max_count)
            if info == False:
                raise UserWarning, 'tried %d times to get a game without player %d' % ( max_count, player_id )
            self.id2info[info['game_id']] = info
            game = CardstoriesGame(self.service, info['game_id'])
            yield self.service.db.runInteraction(game.load)
            self.service.game_init(game)
            defer.returnValue({'game_id': info['game_id']})
        else:
            defer.returnValue(result)
