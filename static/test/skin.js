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
        'owner_index': 0,
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
        'owner_index': 0,
        'ready': true,
        'sentence': 'long sentence is in the flux',
        'winner_card': 7,
        'countdown_finish': $.now() + 60000,
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
        'owner_index': 0,
        'player_index': 5,
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
        'owner_index': 0,
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
        'owner_index': 0,
        'player_index': 3,
        'self': [33, null, [11,12,13,14,15,16,17]],
        'sentence': 'long sentence is in the flux',
        'players': [ [ 'Owner', null, 'n', 30, [] ],
                     [ 'Player 1', null, 'n', '', [] ],
                     [ 'Player 2', null, 'n', null, [] ],
                     [ 'Player 3', null, 'n', 33, [] ],
                     [ 'Player 4', null, 'n', '', [] ] ]
      };
      $.cardstories.invitation_pick_wait('Player 3', game, root);
    } else if(skin == 'invitation_pick_wait_to_vote_voter') {
        old_game = {
            'id': 100,
            'board': [33,11,12,13,14,15],
            'owner_index': 0,
            'player_index': 3,
            'self': [33, null, [11,12,13,14,15,33]],
            'sentence': 'long sentence is in the flux',
            'players': [['Owner', null, 'n', '', null, 42],
                        ['Player 1', null, 'n', '', null, 44],
                        ['Player 2', null, 'n', null, null, 55],
                        ['Player 3', null, 'n', 33, [11,12,13,14,15,33], 66],
                        ['Player 4', null, 'n', '', null, 77]]
        };
        game = $.extend(true, {}, old_game);
        game.players.splice(2,1);
        game.player_index = 2;
        $.cardstories.invitation_pick_wait('Player 3', old_game, root).done(function() {
            window.setTimeout(function() {
                $.cardstories.invitation_pick_wait_to_vote_voter('Player 3', old_game, game, root);
            }, 1000);
        });
    } else if(skin == 'vote_voter') {
      game = {
        'id': 100,
        'owner': false,
        'owner_index': 0,
        'player_index': 2,
        'ready': true,
        'board': [32,31,30,33,35,34],
        'self': [32, null, [32,31,30,33,35,34]],
        'sentence': 'Fake sentence is fake',
        'players': [ [ 'Owner', null, 'n', '', null ],
                     [ 'Player 1', null, 'n', '', null ],
                     [ 'Player 2', null, 'n', 32, [32,31,30,33,35,34] ],
                     [ 'Player 3', null, 'n', '', null ],
                     [ 'Player 4', null, 'n', '', null ],
                     [ 'Player 5', null, 'n', '', null ] ]
      };
      $.cardstories[skin]('Player 2', game, root);
    } else if(skin == 'vote_voter_wait') {
      game = {
        'id': 100,
        'owner': false,
        'owner_index': 0,
        'player_index': 2,
        'ready': true,
        'board': [32,31,33,30,35,34],
        'self': [32, 30, [32,31,30,33,35,34]],
        'sentence': 'Fake sentence is fake',
        'players': [ [ 'Owner', null, 'n', '', null ],
                     [ 'Player 1', null, 'n', '', null ],
                     [ 'Player 2', 30, 'n', 32, [32,31,30,33,35,34]],
                     [ 'Player 3', '', 'n', '', null ],
                     [ 'Player 4', null, 'n', '', null ],
                     [ 'Player 5', '', 'n', '', null ] ]
      };
      $.cardstories[skin]('Player 2', game, root);
    } else if(skin == 'vote_voter_wait_to_complete') {
        old_game = {
            'id': 100,
            'owner': false,
            'owner_index': 0,
            'player_index': 2,
            'ready': true,
            'board': [32,31,33,30,35,34],
            'self': [32, 30, [1,2,3,4,5,32]],
            'winner_card': null,
            'sentence': 'Fake sentence is fake',
            'players': [['Owner', null, 'n', '', null, 11],
                        ['Lucy', '', 'n', '', null, 22],
                        ['Mike', '', 'n', 32, [1,2,3,4,5,32], 33],
                        ['Bob', '', 'n', '', null, 44],
                        ['Mike', null, 'n', '', null, 55],
                        ['Sarah', '', 'n', '', null, 66]]
        };
        game = $.extend(true, {}, old_game);
        game.winner_card = 30;
        game.players[0] = ['Owner', null, 'y', 30, null, 11];
        game.players[1] = ['Lucy', 35, 'n', 31, null, 22];
        game.players[2] = ['Mike', 30, 'y', 32, [1,2,3,4,5,32], 33],
        game.players[3] = ['Bob', 35, 'n', 33, null, 44];
        game.players[5] = ['Sarah', 30, 'y', 35, null, 66];
        game.players.splice(4,1);
        $.cardstories.vote_voter_wait('Player 2', old_game, root).done(function() {
            window.setTimeout(function() {
                $.cardstories.vote_voter_wait_to_complete('Player 2', old_game, game, root);
            }, 1000);
        });
    } else if(skin == 'vote_anonymous') {
      game = {
        'id': 100,
        'owner': false,
        'owner_index': 0,
        'ready': true,
        'board': [32,31,33,30,35,34],
        'self': null,
        'sentence': 'Fake sentence is fake',
        'players': [ [ 'Owner', null, 'n', '', null ],
                     [ 'Player 1', null, 'n', '', null ],
                     [ 'Player 3', '', 'n', '', null ],
                     [ 'Player 4', null, 'n', '', null ],
                     [ 'Player 5', '', 'n', '', null ] ]
      };
      $.cardstories.vote_anonymous(null, game, root);
    } else if(skin == 'vote_owner') {
      game = {
        'id': 100,
        'owner': true,
        'owner_index': 0,
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
        'owner_index': 0,
        'ready': true,
        'sentence': 'the game sentence',
        'board': [32,31,30,33,35,34],
        'winner_card': 30,
        'countdown_finish': $.now() + 15000,
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
        'owner_index': 0,
        'player_index': 1,
        'ready': true,
        'sentence': 'the game sentence',
        'board': [30,31,32,33],
        'self': [31, 30, [1,2,3,4,5,31]],
        'winner_card': 30,
        'players': [['Owner', null, 'n', 30, []],
                     ['Player 1', 32, 'y', 31, []],
                     ['Player 2', null, 'n', 32, []],
                     ['Player 4', 30, 'y', 34, []]]
      };
      $.cardstories.complete_complete('Player 1', game, root);
    } else if(skin == 'complete_owner') {
      game = {
        'id': 100,
        'owner': true,
        'owner_index': 0,
        'ready': true,
        'sentence': 'the game sentence',
        'board': [30,31,32,33,34,35],
        'winner_card': 30,
        'players': [['Owner', null, 'y', 30, []],
                    ['Player 1', 32, 'n', 31, []],
                    ['Player 2', 30, 'y', 32, []],
                    ['Player 3', 35, 'n', 33, []],
                    ['Player 4', 30, 'y', 34, []],
                    ['Player 5', 30, 'y', 35, []]]
      };
      $.cardstories.complete_complete('Owner', game, root);
    } else if(skin == 'complete_anonymous') {
      game = {
        'id': 100,
        'owner': false,
        'owner_index': 0,
        'ready': true,
        'sentence': 'the game sentence',
        'board': [30,31,32,33,34,35],
        'winner_card': 30,
        'players': [['Owner', null, 'y', 30, []],
                    ['Player 1', 32, 'n', 31, []],
                    ['Player 2', 30, 'y', 33, []],
                    ['Player 3', null, 'n', 32, []],
                    ['Player 4', 30, 'y', 34, []],
                    ['Player 5', 30, 'y', 35, []]]
      };
      $.cardstories.complete_complete('Player 3', game, root);
    } else if(skin == 'email') {
      $.cardstories.email(undefined, root);
    } else if(skin == 'credits') {
      $.cardstories.credits(root);
      $('.cardstories_credits_short', root).click();
    }
  };

})(jQuery);
