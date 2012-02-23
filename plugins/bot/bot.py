# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Farsides <contact@farsides.com>
#
# Authors:
#          Xavier Antoviaque <xavier@antoviaque.org>
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

# Imports ##################################################################

import os, random, operator, re, nltk, json
from lxml import objectify

from twisted.internet import defer, reactor
from twisted.python import log

from cardstories.game import CardstoriesGame
from cardstories.service import CardstoriesServiceConnector
from plugins.bot import buildwordsscores


# Functions ###############################################################

def get_delay(delay_dict):
    """Returns a delay, based on a base (minimum) time, plus an additional random part.
    delay_dict = {'base': <seconds>, 'random': <seconds> }"""

    return delay_dict['base'] + random.random() * delay_dict['random']

def call_later(delay_dict, *args, **kwargs):
    """Implements reactor.callLater with a delay with a random part (see get_delay)"""

    delay = get_delay(delay_dict)
    reactor.callLater(delay, *args, **kwargs)


# Classes #################################################################

class Plugin(CardstoriesServiceConnector):
    """
    Bots who join games when there isn't enough players, and try to take a good guess
    at the cards, using data from previous games.
    
    """
    def __init__(self, service, plugins):
        # Register a function to listen to the game events. 
        self.service = service
        self.service.listen().addCallback(self.self_notify)

        # Implement the path conventions
        self.confdir = os.path.join(self.service.settings['plugins-confdir'], self.name())
        self.libdir = os.path.join(self.service.settings['plugins-libdir'], self.name())

        # Load bots logic
        brain = NLWordMatcherBrain(self)

        # Load configuration and instantiate bots
        self.settings = objectify.parse(open(os.path.join(self.confdir, 'bot.xml'))).getroot()
        self.delays = {}
        self.bots = []
        for node in self.settings.iterchildren():
            if node.tag == "delay":
                self.delays[node.get('type')] = {'base': int(node.get('base')),
                                                 'random': int(node.get('random'))}
            elif node.tag == "botinstance":
                bot = Bot(self, brain, int(node.get('player_id')))
                self.bots.append(bot)

    def name(self):
        """
        Method required by all plugins to inspect the plugin's name.
        
        """
        return 'bot'

    def self_notify(self, changes):
        """
        If a 'change' notification is receive of the 'init' type, call the
        appropriate method and reinsert our listen() callback so we get called
        again later, when there's a new event.

        """
        d = defer.succeed(True)
        if changes != None and changes['type'] == 'change':
            details = changes['details']
            if details['type'] == 'set_sentence':
                d = self.joining(changes['game'])
            elif details['type'] == 'voting':
                d = self.voting(changes['game'])
        self.service.listen().addCallback(self.self_notify)
        return d

    def joining(self, game):
        """
        A new game has been created - start monitoring it to check later on if it needs players.
        """

        call_later(self.delays['join'], self.check_need_player, game.id)

        return defer.succeed(True)

    @defer.inlineCallbacks
    def check_need_player(self, game_id):
        """Check newly created games regularly. 
        Make bots join it if there isn't enough players"""

        game, players_ids = yield self.get_game_by_id(game_id)

        # Does the game still need players?
        if game['state'] == 'invitation' and len(players_ids) < CardstoriesGame.NPLAYERS:
            for bot in self.bots:
                if bot.player_id not in players_ids:
                    yield bot.join(game_id)
                    break # Only add one bot every delay

            call_later(self.delays['join'], self.check_need_player, game_id)

        defer.returnValue(True)

    @defer.inlineCallbacks
    def voting(self, game):
        """A game entered the voting phase - notify bots who are playing it"""

        players_ids = yield self.get_players_by_game_id(game.id)

        for bot in self.bots:
            if bot.player_id in players_ids:
                call_later(self.delays['vote'], bot.vote, game.id)

        defer.returnValue(True)


class Bot(CardstoriesServiceConnector):
    """Implements a single bot, which connects to games and play"""

    def __init__(self, plugin, brain, player_id):
        self.plugin = plugin
        self.service = self.plugin.service
        self.brain = brain
        self.player_id = player_id

    @defer.inlineCallbacks
    def join(self, game_id):
        """Join a game and start playing"""

        game, players_ids = yield self.get_game_by_id(game_id, player_id=self.player_id)

        if game['state'] != 'invitation':
            log.msg("Bot %d tried to join game %d, but game wasn't accepting new players" % (self.player_id, game['id']))
            defer.returnValue(False)
        else:
            yield self.plugin.service.handle([], {'action': ['participate'],
                                                  'player_id': [self.player_id],
                                                  'game_id': [game_id]})
            log.msg("Bot %d joined game %d" % (self.player_id, game_id))

            call_later(self.plugin.delays['pick'], self.pick, game_id)

            defer.returnValue(True)

    @defer.inlineCallbacks
    def pick(self, game_id):
        """Pick a card during the first phase of the game"""

        game, players_ids = yield self.get_game_by_id(game_id, player_id=self.player_id)

        # Check the game hasn't gone to vote without us
        if game['state'] != 'invitation' or self.player_id not in players_ids:
            log.msg("Bot %d didn't get enough time to pick on game %d" % (self.player_id, game['id']))
            defer.returnValue(False)
        else:
            my_cards = game['self'][2]

            picked_card = yield self.brain.choose_card_to_pick(game['sentence'], my_cards)

            yield self.plugin.service.handle([], {'action': ['pick'],
                                                  'player_id': [self.player_id],
                                                  'card': [picked_card],
                                                  'game_id': [game_id]})

            log.msg("Bot %d picked card %d on game %d" % (self.player_id, picked_card, game['id']))

            defer.returnValue(True)

    @defer.inlineCallbacks
    def vote(self, game_id):
        """Vote for a card during the second phase of the game"""

        game, players_ids = yield self.get_game_by_id(game_id, player_id=self.player_id)
        board = game['board']

        # Check the game hasn't gone to vote without us
        if game['state'] != 'vote' or self.player_id not in players_ids:
            log.msg("Bot %d didn't get enough time to vote on game %d" % (self.player_id, game['id']))
            defer.returnValue(False)
        else:
            # Don't try to pick the card we chose
            my_card = game['self'][0]
            board_without_my_card = [x for x in board if x != my_card]

            voted_card = yield self.brain.choose_card_to_vote(game['sentence'], board_without_my_card)

            yield self.plugin.service.handle([], {'action': ['vote'],
                                           'player_id': [self.player_id],
                                           'card': [voted_card],
                                           'game_id': [game['id']]})

            log.msg("Bot %d voted for card %d on game %d" % (self.player_id, voted_card, game['id']))

            defer.returnValue(True)


class Brain(object):
    """Object able to make informed decisions about cards to pick/vote"""

    def __init__(self, plugin):
        self.plugin = plugin

    @defer.inlineCallbacks
    def choose_card_to_pick(self, sentence, cards):
        """Among a set of cards, choose one to pick for the first phase of the game"""

        ranked_cards = yield self.sort_cards_by_ranking_for_sentence(sentence, cards)
        card = ranked_cards[0][0] # best choice

        defer.returnValue(card)

    @defer.inlineCallbacks
    def choose_card_to_vote(self, sentence, cards):
        """Among a set of cards, choose one to vote for in the second phase of the game"""

        ranked_cards = yield self.sort_cards_by_ranking_for_sentence(sentence, cards)
        card = self.weighted_card_choice(ranked_cards)

        defer.returnValue(card)


    @defer.inlineCallbacks
    def sort_cards_by_ranking_for_sentence(self, sentence, cards):
        """Builds a list of the cards, ranked by decreasing order of pertinence for sentence"""

        all_cards_scores = yield self.get_all_cards_scores_for_sentence(sentence)

        available_cards_scores = (x for x in all_cards_scores.iteritems() if x[0] in cards)
        ranked_cards = sorted(available_cards_scores, key=operator.itemgetter(1), reverse=True)

        log.msg("Bot brain computed scores for cards %s on sentence '%s' (card_id, score): %s" % \
                                    (cards, sentence.strip().encode('utf-8'), repr(ranked_cards)))

        defer.returnValue(ranked_cards)

    def get_all_cards_scores_for_sentence(self, sentence):
        """Builds a dictionary of scores for all cards. The score for each represents
        how well the card matches the sentence (the higher, the better).
        Format: { <card_id>: <score>, ... }
        
        To subclass."""

        raise NotImplementedError

    def weighted_card_choice(self, ranked_cards):
        """Random choice of a card in the list, weighted by score"""

        offset = random.randint(0, sum((x[1] for x in ranked_cards)))
        for card, score in ranked_cards:
            if offset <= score:
                return card
            offset -= score

    def create_zero_cards_scores_dict(self):
        cards_scores = {}
        for card_id in xrange(1, CardstoriesGame.NCARDS + 1):
            cards_scores[card_id] = 0
        return cards_scores


class NLWordMatcherBrain(Brain):
    """Score cards by matching each word of the story individually 
    to sentences used to describe the cards in previously completed stories
    
    Natural language version - use predefined word lists, compiled using natural language techniques
    See buildwordsscores.py"""

    def get_all_cards_scores_for_sentence(self, sentence):

        sentence_token_list = nltk.word_tokenize(sentence)
        sentence_word_list = buildwordsscores.normalize_word_list(sentence_token_list)

        cards_words_scores_filename = self.plugin.settings.get('cards_words_scores_filename')
        cards_words_scores_path = os.path.join(self.plugin.confdir, cards_words_scores_filename)
        with open(cards_words_scores_path) as f:
            card_word_list = json.load(f)

        all_cards_scores = self.create_zero_cards_scores_dict()
        for sentence_word in sentence_word_list:
            for card, card_words in card_word_list.iteritems():
                if sentence_word in card_words:
                    all_cards_scores[int(card)] += card_words[sentence_word]

        return all_cards_scores


