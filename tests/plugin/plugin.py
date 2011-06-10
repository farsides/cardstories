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
class Plugin:
    
    def __init__(self, service, plugins):
        self.service = service
        self.accept(None)

    def name(self):
        return 'plugin'

    def accept(self, event):
        self.service.plugin_event = event
        if event == None:
            pass
        # startService() was called on CardstoriesService
        elif event['type'] == 'start': 
            pass
        # stopService() is about to be called on CardstoriesService
        elif event['type'] == 'stop': 
            pass
        # a game is about to be deleted from memory
        elif event['type'] == 'delete': 
            event['game'] # CardstoriesGame instance
        # a game was modified
        elif event['type'] == 'change': 
            event['game'] # CardstoriesGame instance
            # a player is given cards to pick
            if event['details']['type'] == 'participate':
                event['details']['player_id'] # numerical player id
            # the author went to voting state
            elif event['details']['type'] == 'voting':
                pass
            # the player picks a card
            elif event['details']['type'] == 'pick':
                event['details']['player_id'] # numerical player id
                event['details']['card'] # numerical card id
            # the player votes for a card
            elif event['details']['type'] == 'vote':
                event['details']['player_id'] # numerical player id
                event['details']['vote'] # numerical card id
            # the author went to game complete state
            elif event['details']['type'] == 'complete':
                pass
            # the author invited players to play
            elif event['details']['type'] == 'invite':
                event['details']['invited'] # list of numerical player ids
        self.service.listen().addCallback(self.accept)

    def preprocess(self, result, request):
        request.preprocess = 'preprocess'
        return result

    def postprocess(self, result):
        result['postprocess'] = self.preprocess
        return result

