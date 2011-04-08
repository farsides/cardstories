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
module("cardstories");

function setup() {
    $.cardstories.setTimeout = function(cb, delay) { return window.setTimeout(cb, delay); };
    $.cardstories.ajax = function(o) { return jQuery.ajax(o); };
}

test("subscribe", function() {
    setup();
    expect(5);

    var player_id = 'PLAYER';
    var game_id = undefined;
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 0);
    $.cardstories.name(game_id, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 1);
    equal($.cookie('CARDSTORIES_ID'), null);
    $('#qunit-fixture .cardstories_subscribe .cardstories_name').val(player_id);
    // any ajax issued as indirect side effect of subscribing is ignored because it is
    // not a direct side effect
    $.cardstories.ajax = function(options) {};
    $('#qunit-fixture .cardstories_subscribe .cardstories_submit').click();
    equal($.cookie('CARDSTORIES_ID'), player_id);
    $.cookie('CARDSTORIES_ID', null);
    equal($.cookie('CARDSTORIES_ID'), null);
});

test("widget subscribe", function() {
    setup();
    expect(3);

    equal($.cookie('CARDSTORIES_ID'), null);
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 0);
    $('#qunit-fixture .cardstories').cardstories(undefined, undefined);
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 1);
});

test("sendGame get", function() {
    setup();
    expect(5);
    stop();

    var player_id = 15;
    var game_id = 101;

    var game = $.cardstories.game;
    $.cardstories.game = function(arg_player_id, arg_game_id, root) {
	equal(arg_player_id, player_id);
	equal(arg_game_id, game_id);
	ok($(root).hasClass('cardstories_root'), 'cardstories_root');
	$.cardstories.game = game;
	start();
    };
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?QUERY');
	options.success({}, 'status');
    };

    $('#qunit-fixture .cardstories').addClass('cardstories_root');
    $.cardstories.sendGame(player_id, game_id, $('#qunit-fixture .cardstories_create'), 'QUERY');
});

test("sendGame post", function() {
    setup();
    expect(6);
    stop();

    var player_id = 15;
    var game_id = 101;

    var game = $.cardstories.game;
    $.cardstories.game = function(arg_player_id, arg_game_id, root) {
	equal(arg_player_id, player_id);
	equal(arg_game_id, game_id);
	ok($(root).hasClass('cardstories_root'), 'cardstories_root');
	$.cardstories.game = game;
	start();
    };
    $.cardstories.ajax = function(options) {
        equal(options.type, 'POST');
        equal(options.url, $.cardstories.url + '?QUERY');
        equal(options.data, 'DATA');
	options.success({}, 'status');
    };

    $('#qunit-fixture .cardstories').addClass('cardstories_root');
    $.cardstories.sendGame(player_id, game_id, $('#qunit-fixture .cardstories_create'), 'QUERY', 'DATA');
});

test("create", function() {
    setup();
    expect(7);

    var player_id = 15;
    var card = 1;
    var sentence = 'SENTENCE';

    $.cardstories.ajax = function(options) {
        equal(options.type, 'POST');
        equal(options.url, $.cardstories.url + '?action=create&owner_id=' + player_id + '&card=' + card);
	equal(options.data, 'sentence=' + sentence);
    };

    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 0, 'pick_card not active');
    $.cardstories.create(player_id, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 1, 'pick_card active');
    equal($('#qunit-fixture .cardstories_create .cardstories_write_sentence.cardstories_active').length, 0, 'sentence not active');
    $('#qunit-fixture .cardstories_create .cardstories_pick_card img:nth(0)').click();
    equal($('#qunit-fixture .cardstories_create .cardstories_write_sentence.cardstories_active').length, 1, 'sentence active');
    $('#qunit-fixture .cardstories_create .cardstories_write_sentence .cardstories_sentence').val(sentence);
    $('#qunit-fixture .cardstories_create .cardstories_write_sentence .cardstories_submit').click();
});

test("widget lobby", function() {
    setup();
    expect(4);

    var player_id = 15;

    ok(!$('#qunit-fixture .cardstories').hasClass('cardstories_root'), 'no cardstories_root');
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=lobby&player_id=' + player_id + '&in_progress=true&my=true');
    };
    $('#qunit-fixture .cardstories').cardstories(player_id);
    ok($('#qunit-fixture .cardstories').hasClass('cardstories_root'), 'cardstories_root');
});

test("game", function() {
    setup();
    expect(4);

    var player_id = 15;
    var game_id = 101;
    var card = 1;
    var sentence = 'SENTENCE';

    $.cardstories.fake_state = function(inner_player_id, game, element) {
	equal(inner_player_id, player_id);
	equal(game.id, game_id);
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=game&game_id=' + game_id + '&player_id=' + player_id);
	var game = {
	    'id': game_id,
	    'state': 'fake_state'
	};
	options.success(game);
    };

    $.cardstories.game(player_id, game_id, $('#qunit-fixture .cardstories'));
});

test("invitation_owner", function() {
    setup();
    expect(12);

    var player1 = 'player1';
    var card1 = 5;
    var player2 = 'player2';
    var player_id = player1;
    var game_id = 101;

    var game = {
	'id': game_id,
	'owner': true,
	'ready': true,
        'players': [ [ player1, null, 'n', card1, [] ],
                     [ player2, null, 'n', null, [] ] ]
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=voting&owner_id=' + player_id + '&game_id=' + game_id);
    };

    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 0);
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    var cards = $('#qunit-fixture .cardstories_invitation .cardstories_owner .cardstories_cards');
    equal($('.cardstories_card:nth(0)', cards).attr('title'), player1);
    equal($('.cardstories_card:nth(0)', cards).attr('src'), 'PATH/card0' + card1 + '.png');
    equal($('.cardstories_card:nth(1)', cards).attr('title'), player2);
    equal($('.cardstories_card:nth(1)', cards).attr('src'), 'PATH/card-back.png');
    equal($('.cardstories_card:nth(2)', cards).attr('title'), 'Waiting');
    equal($('.cardstories_card:nth(2)', cards).attr('src'), 'PATH/card-back.png');
    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 1);
    equal($('#qunit-fixture .cardstories_owner .cardstories_invite').attr('href'), '?game_id=' + game.id);
    equal($('#qunit-fixture .cardstories_owner .cardstories_refresh').attr('href'), '?player_id=' + player_id + '&game_id=' + game.id);
    $('#qunit-fixture .cardstories_owner .cardstories_voting').click();
});

test("invitation_pick", function() {
    setup();
    expect(7);

    var player_id = 15;
    var game_id = 101;
    var picked_before = 3;
    var picked_after = 5;
    var cards = [1,2,picked_before,4,picked_after,5];
    var sentence = 'SENTENCE';

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=pick&player_id=' + player_id + '&game_id=' + game_id + '&card=' + picked_after);
    };

    var game = {
	'id': game_id,
	'self': [picked_before, null, cards],
	'sentence': sentence
    };
    equal($('#qunit-fixture .cardstories_invitation .cardstories_pick.cardstories_active').length, 0);    
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_invitation .cardstories_pick.cardstories_active').length, 1);    
    equal($('#qunit-fixture .cardstories_invitation .cardstories_pick .cardstories_sentence').text(), sentence);
    var element = $('#qunit-fixture .cardstories_invitation .cardstories_pick .cardstories_cards');
    equal($('.cardstories_card:nth(0)', element).attr('src'), 'PATH/card0' + cards[0] + '.png');
    equal($('.cardstories_card:nth(5)', element).attr('src'), 'PATH/card0' + cards[5] + '.png');
    $('.cardstories_card:nth(4)', element).click();
});

test("invitation_participate", function() {
    setup();
    expect(5);

    var player_id = 15;
    var game_id = 101;
    var card = 1;
    var sentence = 'SENTENCE';

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=participate&player_id=' + player_id + '&game_id=' + game_id);
    };

    var game = {
	'id': game_id,
	'self': null,
	'sentence': sentence
    };
    equal($('#qunit-fixture .cardstories_invitation .cardstories_participate.cardstories_active').length, 0);
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_invitation .cardstories_participate.cardstories_active').length, 1);
    equal($('#qunit-fixture .cardstories_participate .cardstories_sentence').text(), sentence);
    $('#qunit-fixture .cardstories_participate .cardstories_submit').click();
});

test("widget invitation", function() {
    setup();
    expect(5);

    var player_id = 15;
    var game_id = 101;
    var sentence = 'SENTENCE';

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=game&game_id=' + game_id + '&player_id=' + player_id);
	var game = {
	    'id': game_id,
	    'state': 'invitation',
	    'sentence': sentence
	};
	options.success(game);
	equal($('#qunit-fixture .cardstories_participate .cardstories_sentence').text(), sentence);
    };

    $.cardstories.unset_active('#qunit-fixture .cardstories');
    equal($('#qunit-fixture .cardstories_invitation .cardstories_active').length, 0);
    $('#qunit-fixture .cardstories').cardstories(player_id, game_id);
    equal($('#qunit-fixture .cardstories_invitation .cardstories_active').length, 1);
});

test("vote_voter", function() {
    setup();
    expect(14);

    var player_id = 15;
    var game_id = 101;
    var picked = 2;
    var voted_before = 3;
    var voted_after = 5;
    var board = [1,picked,voted_before,4,voted_after];
    var sentence = 'SENTENCE';

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=vote&player_id=' + player_id + '&game_id=' + game_id + '&card=' + voted_after);
    };

    var game = {
	'id': game_id,
	'board': board,
	'self': [picked, voted_before, [11,12,13,14,15,16,17]],
	'sentence': sentence
    };
    var element = $('#qunit-fixture .cardstories_vote .cardstories_voter');
    $('.cardstories_card:nth(0)', element).attr('title', 'SOMETHING');
    equal($('.cardstories_card:nth(1)', element).attr('title'), '');
    equal($('#qunit-fixture .cardstories_vote .cardstories_voter.cardstories_active').length, 0);
    $.cardstories.vote(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_vote .cardstories_voter.cardstories_active').length, 1);
    equal($('#qunit-fixture .cardstories_voter .cardstories_sentence').text(), sentence);
    for(var i = 0; i < board.length; i++) {
      equal($('.cardstories_card:nth(' + i + ')', element).attr('src'), 'PATH/card0' + board[i] + '.png');
    }
    equal($('.cardstories_card:nth(0)', element).attr('title'), '');
    equal($('.cardstories_card:nth(1)', element).attr('title'), 'My Card');
    equal($('.cardstories_card:nth(5)', element).attr('src'), 'PATH/nocard.png');
    $('.cardstories_picked', element).click(); // must do nothing
    $('.cardstories_card:nth(4)', element).click();
});

test("vote_viewer", function() {
    setup();
    expect(5);

    var player_id = 15;
    var game_id = 101;
    var board = [1,2,3,4,5,6,7];
    var sentence = 'SENTENCE';

    var game = {
	'id': game_id,
	'board': board,
	'self': null,
	'sentence': sentence
    };
    equal($('#qunit-fixture .cardstories_vote .cardstories_viewer.cardstories_active').length, 0);
    $.cardstories.vote(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_vote .cardstories_viewer.cardstories_active').length, 1);
    equal($('#qunit-fixture .cardstories_viewer .cardstories_sentence').text(), sentence);
    equal($('#qunit-fixture .cardstories_viewer .cardstories_card1').metadata().card, 1);
    equal($('#qunit-fixture .cardstories_viewer .cardstories_card7').metadata().card, 7);
});

test("vote_owner", function() {
    setup();
    expect(9);

    var player_id = 15;
    var game_id = 101;

    var voter11 = 11;
    var voter12 = 12;
    var voter21 = 21;

    var board1 = 30;
    var board2 = 31;
    var board = [ board1, board2 ];

    var sentence = 'SENTENCE';

    var game = {
	'id': game_id,
	'owner': true,
        'sentence': sentence,
        'board': board,
        'players': [ [ voter11, board1, 'n', null, [ ] ],
                     [ voter12, board2, 'n', null, [ ] ],
                     [ voter21, board1, 'n', null, [ ] ]
                   ],
	'ready': true
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=complete&owner_id=' + player_id + '&game_id=' + game_id);
    };

    equal($('#qunit-fixture .cardstories_vote .cardstories_owner.cardstories_active').length, 0);
    $.cardstories.vote(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_vote .cardstories_owner.cardstories_active').length, 1);
    var vote = $('#qunit-fixture .cardstories_vote .cardstories_owner');
    equal($('.cardstories_sentence', vote).text(), sentence);
    ok($('.cardstories_finish', vote).hasClass('cardstories_ready'), 'cardstories_ready');
    var first = $('.cardstories_card:nth(0)', vote);
    equal($('.cardstories_votes:nth(0) .cardstories_result:nth(0)', vote).text(), voter11.toString());
    equal($('.cardstories_votes:nth(0) .cardstories_result:nth(1)', vote).text(), voter21.toString());
    equal($('.cardstories_votes:nth(1) .cardstories_result:nth(0)', vote).text(), voter12.toString());
    
    $('.cardstories_finish', vote).click();
});

test("complete", function() {
    setup();
    expect(21);

    var game_id = 101;

    var voter11 = 11;
    var voter12 = 12;
    var voter21 = 21;

    var board1 = 30;
    var board2 = 31;
    var board3 = 32;

    var board = [ board1, board2, board3 ];

    var sentence = 'SENTENCE';

    var game = {
	'id': game_id,
	'owner': true,
        'sentence': sentence,
        'board': board,
        'winner_card': board1,
        'players': [ [ voter11, board1, 'y', board3, [ ] ],
                     [ voter12, null, 'y', board1, [ ] ],
                     [ voter21, board1, 'n', board2, [ ] ]
                   ],
	'ready': true
    };

    equal($('#qunit-fixture .cardstories_complete.cardstories_active').length, 0);
    $.cardstories.complete(voter12, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_complete.cardstories_active').length, 1);

    var element = $('#qunit-fixture .cardstories_complete');
    equal($('.cardstories_sentence', element).text(), sentence);
    
    var i;
    for(i = 0; i < board.length; i++) {
      ok($('.cardstories_column:nth(' + i + ')', element).is(':visible'), 'column ' + i + ' is visible');
    }
    for(i = board.length; i < 6; i++) {
      ok(!$('.cardstories_column:nth(' + i + ')', element).is(':visible'), 'column ' + i + ' is not visible');
    }

    var column;
    column = $('.cardstories_column:nth(0)', element);
    equal($('.cardstories_card', column).metadata().card, board1);
    equal($('.cardstories_player', column).text(), voter12.toString());
    ok($('.cardstories_player', column).hasClass('cardstories_win'), 'cardstories_win');
    equal($('.cardstories_voter:nth(0)', column).text(), voter11.toString());
    ok($('.cardstories_voter:nth(0)', column).is(':visible'), 'col 1, first vote visible');
    equal($('.cardstories_voter:nth(1)', column).text(), voter21.toString());
    ok($('.cardstories_voter:nth(1)', column).is(':visible'), 'col 1, second vote visible');
    ok(!$('.cardstories_voter:nth(2)', column).is(':visible'), 'col 1, third vote hidden');

    column = $('.cardstories_column:nth(1)', element);
    equal($('.cardstories_card', column).metadata().card, board2);
    equal($('.cardstories_player', column).text(), voter21.toString());
    ok(!$('.cardstories_player', column).hasClass('cardstories_win'), 'cardstories_win not set');
    ok(!$('.cardstories_voter:nth(0)', column).is(':visible'), 'col 2, first vote hidden');
    
  });

test("advertise", function() {
    setup();
    expect(2);
    
    var owner_id = 15;
    var game_id = 100;

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=invite&owner_id=' + owner_id + '&game_id=' + game_id + '&player_id=player1&player_id=player2');
    };

    var element = $('#qunit-fixture .cardstories_advertise');
    $('.cardstories_text', element).text(" \n \t player1 \n\n   \nplayer2");
    $.cardstories.advertise(owner_id, game_id, $('#qunit-fixture .cardstories'));
    $('.cardstories_submit', element).click();
  });

test("lobbyInProgress", function() {
    setup();
    expect(29);

    var player_id = 10;
    var game1 = 100;
    var sentence1 = 'sentence1';
    var game2 = 101;
    var sentence2 = 'sentence2';
    var game3 = 102;
    var sentence3 = 'sentence3';
    var games = {'games': [[game1, sentence1, 'invitation', 0],
                           [game2, sentence2, 'vote', 1],
                           [game3, sentence3, 'invitation', 0]
                          ],
                 'wins': {}
                };
    games.wins[game1] = 'n';
    games.wins[game2] = 'n';
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 0, 'in_progress not active');
    $.cardstories.lobbyInProgress(player_id, games, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 1, 'in_progress active');
    var element = $('#qunit-fixture .cardstories_in_progress');
    // lobby tab
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=lobby&player_id=' + player_id + '&in_progress=false&my=true');
    };
    $('.cardstories_tab', element).click();
    // list of games
    ok($('.cardstories_games tbody tr:nth(0)', element).is(':visible'), 'first row is visible');
    ok($('.cardstories_games tbody tr:nth(1)', element).is(':visible'), 'second row is visible');
    equal($('.cardstories_games tbody tr', element).length, 2, 'only two rows visible');
    // check that the rows content match what is expected
    var first = $('.cardstories_games tbody tr:nth(0)', element);
    ok($('.cardstories_lobby_role', first).hasClass('cardstories_lobby_player'), 'role player');
    equal($('.cardstories_lobby_state', first).text(), 'invitation');
    equal($('.cardstories_lobby_sentence', first).text(), sentence1);
    equal($('.cardstories_lobby_sentence', first).metadata({type: "attr", name: "data"}).game_id, game1);
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=game&game_id=' + game1 + '&player_id=' + player_id);
    };
    $('.cardstories_lobby_sentence', first).click();
    var second = $('.cardstories_games tbody tr:nth(1)', element);
    ok($('.cardstories_lobby_role', second).hasClass('cardstories_lobby_owner'), 'role owner');
    equal($('.cardstories_lobby_state', second).text(), 'vote');
    equal($('.cardstories_lobby_sentence', second).text(), sentence2);
    equal($('.cardstories_lobby_sentence', second).metadata({type: "attr", name: "data"}).game_id, game2);
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=game&game_id=' + game2 + '&player_id=' + player_id);
    };
    $('.cardstories_lobby_sentence', second).click();
    // modify the number row per page
    $('.cardstories_pager select', element).val(1);
    $('.cardstories_pager select', element).change();
    equal($('.cardstories_games tbody tr:nth(0) .cardstories_lobby_sentence', element).text(), sentence1);
    ok($('.cardstories_games tbody tr:nth(0)', element).is(':visible'), 'first row is visible');
    equal($('.cardstories_games tbody tr', element).length, 1, 'only one row visible');
    // go to last page
    $('.cardstories_pager .last', element).click();
    equal($('.cardstories_games tbody tr:nth(0) .cardstories_lobby_sentence', element).text(), sentence3);
    // go to first page
    $('.cardstories_pager .first', element).click();
    equal($('.cardstories_games tbody tr:nth(0) .cardstories_lobby_sentence', element).text(), sentence1);
    // go to next page
    $('.cardstories_pager .next', element).click();
    equal($('.cardstories_games tbody tr:nth(0) .cardstories_lobby_sentence', element).text(), sentence2);
    // go to previous page
    $('.cardstories_pager .prev', element).click();
    equal($('.cardstories_games tbody tr:nth(0) .cardstories_lobby_sentence', element).text(), sentence1);
    // create game
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 0, 'pick_card not active');
    $('.cardstories_start_story', element).click();
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 0, 'in_progress not active');
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 1, 'pick_card active');
  });
