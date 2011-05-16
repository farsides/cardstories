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

  $.cardstories.skin = function(what, root) {
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
    if(skin == 'advertise') {
      $.cardstories.advertise('PLAYER1', 100, root);
    } else if(skin == 'in_progress') {
      $.cardstories.lobby_in_progress('PLAYER1', lobby, root);
    } else if(skin == 'finished') {
      $.cardstories.lobby_finished('PLAYER1', lobby, root);
    } else if(skin == 'create_pick_card') {
      $.cardstories.create_pick_card('PLAYER1', root);
    } else if(skin == 'create_write_sentence') {
      $.cardstories.create_write_sentence('PLAYER1', 5, root);
    } else if(skin == 'invitation_owner') {
      var game = {
	'id': 100,
	'owner': true,
	'ready': true,
        'players': [ [ 'player1', null, 'n', 5, [] ],
                     [ 'player2', null, 'n', null, [] ] ]
      };

      $.cardstories.invitation_owner('PLAYER1', game, root);
    } else if(skin == 'invitation_pick') {
      var game = {
	'id': 100,
	'self': [5, null, [11,12,13,14,15,16,17]],
	'sentence': 'long sentence is in the flux'
      };
      $.cardstories.invitation_pick('PLAYER1', game, root);
    } else if(skin == 'invitation_pick_wait') {
      var game = {
	'id': 100,
	'self': [5, null, [11,12,13,14,15,16,17]],
	'sentence': 'long sentence is in the flux'
      };
      $.cardstories.invitation_pick_wait('PLAYER1', game, root);
    } else if(skin == 'vote_voter' || skin == 'vote_owner' || skin == 'vote_viewer') {
      var game = {
	'id': 100,
	'board': [21,22,23,24,25,26],
	'self': [21, 26, [21,12,13,14,15,16,17]],
	'sentence': 'The sentence is the sentence'
      };
      $.cardstories[skin]('PLAYER1', game, root);
    } else if(skin == 'complete') {
      var game = {
	'id': 100,
	'owner': false,
        'sentence': 'the game sentence',
        'board': [30,31,32],
        'winner_card': 30,
        'players': [ [ 'voter11', 30, 'y', 32, [ ] ],
                     [ 'voter12', null, 'y', 30, [ ] ],
                     [ 'voter21', 30, 'n', 31, [ ] ]
                   ],
	'ready': true
      };
      $.cardstories.complete('voter11', game, root);
    } else if(skin == 'complete_owner') {
      var game = {
	'id': 100,
	'owner': true,
        'sentence': 'the game sentence',
        'board': [30,31,32],
        'winner_card': 30,
        'players': [ [ 'voter11', 30, 'y', 32, [ ] ],
                     [ 'voter12', null, 'y', 30, [ ] ],
                     [ 'voter21', 30, 'n', 31, [ ] ]
                   ],
	'ready': true
      };
      $.cardstories.complete('voter11', game, root);
    } else if(skin == 'name') {
      $.cardstories.name(undefined, root);
    }
  }

})(jQuery);
