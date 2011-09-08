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
      $.cardstories.create_pick_card('Owner', root);
    } else if(skin == 'create_write_sentence') {
      $.cardstories.create_write_sentence('Owner', 5, root);
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

      $.cardstories.invitation_owner('Owner', game, root);
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

      $.cardstories.invitation_owner('Owner', game, root);
    } else if(skin == 'invitation_pick') {
      game = {
        'id': 100,
        'owner': false,
        'owner_id': 'Owner',
        'sentence': 'long sentence is in the flux',
        'self': [35, null, [11,12,13,14,15,16,17]],
        'players': [ [ 'Owner', null, 'n', 30, [] ],
                     [ 'Player 1', null, 'n', 31, [] ],
                     [ 'Player 2', null, 'n', 32, [] ],
                     [ 'Player 3', null, 'n', 33, [] ],
                     [ 'Player 4', null, 'n', 34, [] ],
                     [ 'Player 5', null, 'n', 35, [] ] ]
      };
      $.cardstories.invitation_pick('Player 5', game, root);
    } else if(skin == 'invitation_anonymous') {
      game = {
        'id': 100,
        'owner': false,
        'owner_id': 'Owner',
        'sentence': 'long sentence is in the flux',
        'players': [ [ 'Owner', null, 'n', 30, [] ],
                     [ 'Player 1', null, 'n', 31, [] ],
                     [ 'Player 2', null, 'n', 32, [] ],
                     [ 'Player 3', null, 'n', 33, [] ],
                     [ 'Player 4', null, 'n', 34, [] ],
                     [ 'Player 5', null, 'n', 35, [] ] ]
      };
      $.cardstories.invitation_anonymous('', game, root);
    } else if(skin == 'invitation_pick_wait') {
      game = {
        'id': 100,
        'owner_id': 'Owner',
        'self': [33, null, [11,12,13,14,15,16,17]],
        'sentence': 'long sentence is in the flux',
        'players': [ [ 'Owner', null, 'n', 30, [] ],
                     [ 'Player 1', null, 'n', '', [] ],
                     [ 'Player 2', null, 'n', null, [] ],
                     [ 'Player 3', null, 'n', 33, [] ],
                     [ 'Player 4', null, 'n', '', [] ] ]
      };
      $.cardstories.invitation_pick_wait('Player 3', game, root);
    } else if(skin == 'pick_wait_to_vote') {
      var players1 = [ [ 'Owner', null, 'n', 30, [] ],
                     [ 'Player 1', null, 'n', '', [] ],
                     [ 'Player 2', null, 'n', null, [] ],
                     [ 'Player 3', null, 'n', 33, [] ],
                     [ 'Player 4', null, 'n', '', [] ] ];
      var players2 = [ [ 'Owner', null, 'n', 30, [] ],
                     [ 'Player 1', null, 'n', '', [] ],
                     [ 'Player 3', null, 'n', 33, [] ],
                     [ 'Player 4', null, 'n', '', [] ] ];
      game = {
        'id': 100,
        'owner_id': 'Owner',
        'self': [33, null, [11,12,13,14,15,16,17]],
        'sentence': 'long sentence is in the flux',
        'players': players1
      };
      $.cardstories.invitation_pick_wait('Player 3', game, root).done(function() {
          game.players = players2;
          $.cardstories.invitation_pick_wait_to_vote_voter('Player 3', game, root);
      });
    } else if(skin == 'vote_voter' || skin == 'vote_voter_wait') {
      game = {
        'id': 100,
        'owner': false,
        'owner_id': 'Owner',
        'ready': true,
        'board': [32,31,30,33,35,34],
        'self': [32, null, [32,31,30,33,35,34]],
        'winner_card': 30,
        'sentence': 'Fake sentence is fake',
        'players': [ [ 'Owner', null, null, 30, [] ],
                     [ 'Player 1', 32, null, 31, [] ],
                     [ 'Player 2', 30, null, 32, [] ],
                     [ 'Player 3', 30, null, 33, [] ],
                     [ 'Player 4', 31, null, 34, [] ],
                     [ 'Player 5', 31, null, 35, [] ] ]
      };
      $.cardstories[skin]('Player 2', game, root);
    } else if(skin == 'vote_anonymous') {
      game = {
        'id': 100,
        'owner': false,
        'owner_id': 'Owner',
        'ready': true,
        'board': [32,31,30,33,35,34],
        'self': null,
        'winner_card': 30,
        'sentence': 'Fake sentence is fake',
        'players': [ [ 'Owner', null, null, 30, [] ],
                     [ 'Player 1', 32, null, 31, [] ],
                     [ 'Player 2', 30, null, 32, [] ],
                     [ 'Player 3', 30, null, 33, [] ],
                     [ 'Player 4', 31, null, 34, [] ],
                     [ 'Player 5', 31, null, 35, [] ] ]
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
      $.cardstories.vote_owner('Owner', game, root);
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
        'players': [ [ 'Owner', null, 'y', 30, [ ] ],
                     [ 'Player 1', 32, 'n', 31, [ ] ],
                     [ 'Player 2', 30, 'y', 32, [ ] ],
                     [ 'Player 3', 35, 'n', 33, [ ] ],
                     [ 'Player 4', 30, 'y', 34, [ ] ],
                     [ 'Player 5', 30, 'y', 35, [ ] ]
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
