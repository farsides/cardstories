//
//     Copyright (C) 2011 Loic Dachary <loic@dachary.org>
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
//
//     You should have received a copy of the GNU General Public License
//     along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
(function($) {

  $.cardstories.skin = function(skin, root) {
    $(root).addClass('cardstories_root');
    var lobby = {'games': [[100, 'sentence100', 'invitation', 0],
                           [101, 'sentence101', 'vote', 1],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0]
                          ],
                 'win': {100: 'n', 101: 'y' }
                };
    var lobby_one = {'games': [[100, 'sentence100', 'invitation', 0],
                               [101, 'sentence101', 'vote', 1]
                              ],
                     'win': {100: 'n', 101: 'y' }
                    };
    var game;
    if(skin == 'in_progress') {
      $.cardstories.lobby_in_progress('PLAYER1', lobby, root);
    } else if(skin == 'in_progress_one') {
      $.cardstories.lobby_in_progress('PLAYER1', lobby_one, root);
    } else if(skin == 'finished') {
      $.cardstories.lobby_finished('PLAYER1', lobby, root);
    } else if(skin == 'create_pick_card') {
      $.cardstories.create_pick_card('PLAYER1', root);
    } else if(skin == 'create_write_sentence') {
      $.cardstories.create_write_sentence('PLAYER1', 5, root);
    } else if(skin == 'invitation_owner') {
      game = {
        'id': 100,
        'owner': true,
        'owner_id': 'Owner',
        'ready': false,
        'sentence': 'long sentence is in the flux',
        'winner_card': 7,
        'players': [ [ 'Owner', null, 'n', null, [] ],
                     [ 'Player 1', null, 'n', null, [] ],
                     [ 'Player 2', null, 'n', 2, [] ] ]
      };

      $.cardstories.invitation_owner('PLAYER1', game, root);
    } else if(skin == 'invitation_owner_ready') {
      game = {
        'id': 100,
        'owner': true,
        'owner_id': 'Owner',
        'ready': true,
        'sentence': 'long sentence is in the flux',
        'winner_card': 7,
        'players': [ [ 'Owner', null, 'n', null, [] ],
                     [ 'Player 1', null, 'n', 1, [] ],
                     [ 'Player 2', null, 'n', 2, [] ],
                     [ 'Player 3', null, 'n', 3, [] ],
                     [ 'Player 4', null, 'n', 4, [] ],
                     [ 'Player 5', null, 'n', 5, [] ] ]
      };

      $.cardstories.invitation_owner('PLAYER1', game, root);
    } else if(skin == 'invitation_pick') {
      game = {
	'id': 100,
	'self': [5, null, [11,12,13,14,15,16,17]],
        'players': [
            [ 'player1', null, 'n', 5, [] ],
            [ 'player2', null, 'n', null, [] ],
            [ 'player3', null, 'n', null, [] ],
            [ 'player4', null, 'n', null, [] ],
            [ 'player5', null, 'n', null, [] ],
            [ 'player6', null, 'n', null, [] ]
        ],
        'owner_id': 'player1',
	'sentence': 'long sentence is in the flux'
      };
      $.cardstories.invitation_pick('player2', game, root);
    } else if(skin == 'invitation_anonymous') {
      game = {
	  'id': null,
          'players': [
              [ 'player1', null, 'n', 5, [] ],
              [ 'player2', null, 'n', null, [] ],
              [ 'player3', null, 'n', null, [] ],
              [ 'player4', null, 'n', null, [] ],
              [ 'player5', null, 'n', null, [] ],
              [ 'player6', null, 'n', null, [] ]
          ],
          'owner_id': 'player1',
	  'sentence': 'long sentence is in the flux'
      };
      $.cardstories.invitation_anonymous('', game, root);
    } else if(skin == 'invitation_pick_wait') {
      game = {
	'id': 100,
	'self': [5, null, [11,12,13,14,15,16,17]],
	'sentence': 'long sentence is in the flux'
      };
      $.cardstories.invitation_pick_wait('PLAYER1', game, root);
    } else if(skin == 'vote_voter' || skin == 'vote_voter_wait' || skin == 'vote_viewer') {
      game = {
	'id': 100,
	'board': [21,22,23,24,25,26],
	'self': [23, 26, [21,12,13,14,15,16,17]],
	'sentence': 'The sentence is the sentence'
      };
      $.cardstories[skin]('PLAYER1', game, root);
    } else if(skin == 'vote_anonymous') {
      game = {
	  'id': null,
	  'board': [21,22,23,24,25,26],
	  'self': null,
          'players': [
              [ 'player1', null, 'n', 5, [] ],
              [ 'player2', null, 'n', null, [] ],
              [ 'player3', null, 'n', null, [] ],
              [ 'player4', null, 'n', null, [] ],
              [ 'player5', null, 'n', null, [] ],
              [ 'player6', null, 'n', null, [] ]
          ],
          'owner_id': 'player1',
	  'sentence': 'The sentence is the sentence'
      };
      $.cardstories.vote_anonymous(null, game, root);
    } else if(skin == 'vote_owner') {
      game = {
        'id': 100,
        'owner': true,
        'owner_id': 'Owner',
	    'ready': false,
        'sentence': 'the game sentence',
        'winner_card': 30,
        'board': [32,31,30,33],
        'players': [ [ 'Owner', null, null, 30, [] ],
                     [ 'Player 1', null, null, 31, [] ],
                     [ 'Player 2', null, null, 32, [] ],
                     [ 'Player 3', 30, null, 33, [] ] ]
      };
      $.cardstories.vote_owner('Owner', game, root);
    } else if(skin == 'vote_owner_ready') {
      game = {
        'id': 100,
        'owner': true,
        'owner_id': 'Owner',
	    'ready': true,
        'sentence': 'the game sentence',
        'board': [32,31,30,33,35,34],
        'winner_card': 30,
        'players': [ [ 'Owner', null, null, 30, [] ],
                     [ 'Player 1', 32, null, 31, [] ],
                     [ 'Player 2', 30, null, 32, [] ],
                     [ 'Player 3', 30, null, 33, [] ],
                     [ 'Player 4', 31, null, 34, [] ],
                     [ 'Player 5', 31, null, 35, [] ] ]
      };
      $.cardstories.vote_owner('voter11', game, root);
    } else if(skin == 'complete') {
      game = {
	    'id': 100,
	    'owner': false,
	    'ready': true,
        'sentence': 'the game sentence',
        'board': [30,31,32,33],
        'winner_card': 30,
        'players': [ [ 'voter11', 30, 'y', 32, [ ] ],
                     [ 'voter12', null, 'y', 30, [ ] ],
                     [ 'voter21', 30, 'n', 31, [ ] ]
                   ]
      };
      $.cardstories.complete('voter11', game, root);
    } else if(skin == 'complete_owner') {
      game = {
	    'id': 100,
	    'owner': true,
        'owner_id': 'Owner',
	    'ready': true,
        'sentence': 'the game sentence',
        'board': [30,31,32,33,34,35],
        'winner_card': 30,
        'players': [ [ 'Owner', null, null, 30, [ ] ],
                     [ 'Player 1', 30, 'y', 31, [ ] ],
                     [ 'Player 2', null, 'y', 32, [ ] ],
                     [ 'Player 3', 30, 'n', 33, [ ] ],
                     [ 'Player 4', 30, 'n', 34, [ ] ],
                     [ 'Player 5', 31, 'n', 35, [ ] ]
                   ]
      };
      $.cardstories.complete('Owner', game, root);
    } else if(skin == 'email') {
      $.cardstories.email(undefined, root);
    } else if(skin == 'credits') {
      $.cardstories.credits(root);
      $('.cardstories_credits_short', root).click();
    }
  };

})(jQuery);
