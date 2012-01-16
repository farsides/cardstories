#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Farsides <contact@farsides.com>
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

############################################################################
# If run as a standalone script, invoke with the following environment 
# variables set:
#
#   - PYTHONPATH (pointing to the root of the cardstories install directory)
#   - PLUGINS_CONFDIR (same as the same-name option passed to the WS)
############################################################################ 


# Imports ##################################################################

from __future__ import division

import nltk, json, os
import sqlite3 as db
from lxml import objectify

from cardstories.game import CardstoriesGame


# Functions ###############################################################

def build_words_scores_file():
    """Produces JSON-encoded ranked words lists for each of the game's cards"""

    words_scores = {}
    for card in xrange(1, CardstoriesGame.NCARDS + 1):
        raw_text = get_card_sentences(card)
        words_scores[card] = get_words_scores(raw_text)


    with open(get_cards_words_scores_filepath(), 'w') as f:
        json.dump(words_scores, f)

def get_cards_words_scores_filepath():
    """Gets the path to the JSON-encoded ranked words list file"""

    plugins_confdir = os.environ['PLUGINS_CONFDIR']
    confdir = os.path.join(plugins_confdir, 'bot')
    settings = objectify.parse(open(os.path.join(confdir, 'bot.xml'))).getroot()
    cards_words_scores_filename = settings.get('cards_words_scores_filename')
    cards_words_scores_filepath = os.path.join(confdir, cards_words_scores_filename)

    return cards_words_scores_filepath

def get_card_sentences(card):
    """Retreive all sentences written for a given card (by id), returns it as
    a concatenated raw text string"""

    conn = db.connect(os.environ['DB'])
    c = conn.cursor()
    c.execute("SELECT games.sentence \
                  FROM games, player2game WHERE \
                          player2game.cards = ? AND \
                          games.id = player2game.game_id AND \
                          player2game.player_id = games.owner_id", [chr(card)])

    card_sentences = u''
    for row in c:
        card_sentences += u'%s\n' % row[0]

    return card_sentences

def get_words_scores(raw_text):
    """Takes a raw string and rank meaningful and normalized words by frequency
    Result: {'normalized word': <nb times used>, ...}"""

    # Categories of words we're interested in
    pos_categories = ('VBG', 'VBD', 'VBN', 'VBP', 'JJ', 'VBZ', 'RP', 'NN', 'RB', 'NNS', \
                      'NNP', 'VB', 'WRB', 'PDT', 'RBS', 'RBR', 'CD', 'NNPS', 'JJS', 'JJR')

    # Isolate words in a list and clean up from extra characters
    token_list = nltk.word_tokenize(raw_text)

    # Categorize words and only keep meaningful ones
    tagged_list = nltk.pos_tag(token_list)
    tagged_filtered_list = [ x[0] for x in tagged_list if x[1] in pos_categories ]

    # Normalize words 
    normalized_list = normalize_word_list(tagged_filtered_list)

    # Compute frequency distribution and sort words by rank
    # Only use words with a minimal size to ensure meaningfulness
    fdist = nltk.FreqDist(normalized_list)
    words_scores = dict([[w, fdist[w]] for w in set(normalized_list) if len(w) >= 3])

    return words_scores

def normalize_word_list(words_list):
    """Remove extra characters, put to lower-case and convert to the word stem 
    (ie common root for similar words such as plural, feminine, etc.)"""

    stemmer = nltk.PorterStemmer()

    cleaned_list = [ x.replace('.', '').replace("'", "").lower() for x in words_list ]
    cleaned_stems_list = [ stemmer.stem(t) for t in cleaned_list ]

    return cleaned_stems_list


# Main ###################################################################

if __name__ == "__main__":
    build_words_scores_file()


