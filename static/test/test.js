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
    $.cardstories.setTimeout = function(cb, delay) { console.log("timeout"); return window.setTimeout(cb, delay); };
    $.cardstories.ajax = function(o) { throw o; };
    $.cardstories.reload = $.cardstories.game_or_lobby;
    $.cardstories.confirm_participate = true;
    $.cardstories.poll_ignore = function() { throw 'poll_ignore'; };
}

test("permalink", function() {
    expect(2);
    equal($.cardstories.permalink(5), '?player_id=5');
    equal($.cardstories.permalink(6, 7), '?player_id=6&game_id=7');
  });

test("subscribe", function() {
    setup();
    expect(5);

    var player_id = 'PLAYER';
    var game_id = undefined;
    $.cookie('CARDSTORIES_ID', null);
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

test("send_game", function() {
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
    $.cardstories.send_game(player_id, game_id, $('#qunit-fixture .cardstories_create'), 'QUERY');
});

test("create", function() {
    setup();
    stop();
    expect(7);

    var player_id = 15;
    var card;
    var sentence = 'SENTENCE';

    $.cardstories.ajax = function(options) {
        equal(options.type, 'POST');
        equal(options.url, $.cardstories.url + '?action=create&owner_id=' + player_id + '&card=' + card);
	equal(options.data, 'sentence=' + sentence);
    };

    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 0, 'pick_card not active');
    $.cardstories.
        create(player_id, $('#qunit-fixture .cardstories')).
        done(function(is_ready) {
            equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 1, 'pick_card active');
            equal($('#qunit-fixture .cardstories_create .cardstories_write_sentence.cardstories_active').length, 0, 'sentence not active');
            var first_card = $('#qunit-fixture .cardstories_create .cardstories_card:nth(0)');
            card = first_card.metadata({type: "attr", name: "data"}).card;
            first_card.click();
            $('#qunit-fixture .cardstories_create .cardstories_card_confirm_ok').click();
            equal($('#qunit-fixture .cardstories_create .cardstories_write_sentence.cardstories_active').length, 1, 'sentence active');
            $('#qunit-fixture .cardstories_create .cardstories_write_sentence .cardstories_sentence').val(sentence);
            $('#qunit-fixture .cardstories_create .cardstories_write_sentence .cardstories_submit').click();
            start();
        });
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

test("invitation_owner_invite_more", function() {
    setup();
    expect(4);

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

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) { };
    $.cardstories.ajax = function(options) { };

    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 0);
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 1);
    $('#qunit-fixture .cardstories_invitation .cardstories_owner .cardstories_invite_friends').click();
    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 0);
    equal($('#qunit-fixture .cardstories_advertise.cardstories_active').length, 1);
});

test("invitation_owner", function() {
    setup();
    stop();
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
        start();
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
        equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
        equal(new_poll, undefined, 'poll_ignore metadata not set');
    };

    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 0);
    $.cardstories.
        invitation(player_id, game, $('#qunit-fixture .cardstories')).
        done(function(is_ready) {
            var cards = $('#qunit-fixture .cardstories_invitation .cardstories_owner .cardstories_cards');
            equal($('.cardstories_card:nth(0) .cardstories_card_foreground', cards).attr('alt'), player1);
            equal($('.cardstories_card:nth(0) .cardstories_card_foreground', cards).attr('src'), 'PATH/card0' + card1 + '.png');
            equal($('.cardstories_card:nth(1) .cardstories_card_foreground', cards).attr('alt'), player2);
            equal($('.cardstories_card:nth(1) .cardstories_card_foreground', cards).attr('src'), 'PATH/card-back.png');
            equal($('.cardstories_card:nth(2) .cardstories_card_foreground', cards).attr('alt'), 'Waiting');
            equal($('.cardstories_card:nth(2) .cardstories_card_foreground', cards).attr('src'), 'PATH/card-back.png');
            equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 1);
            $('#qunit-fixture .cardstories_owner .cardstories_voting').click();
        });
});

test("invitation_pick", function() {
    setup();
    stop();
    expect(11);

    var player_id = 15;
    var game_id = 101;
    var picked = 5;
    var cards = [1,2,3,4,picked,5];
    var sentence = 'SENTENCE';

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=pick&player_id=' + player_id + '&game_id=' + game_id + '&card=' + picked);
    };

    var game = {
	'id': game_id,
	'self': [null, null, cards],
	'sentence': sentence
    };

    equal($('#qunit-fixture .cardstories_invitation .cardstories_pick.cardstories_active').length, 0);
    var element = $('#qunit-fixture .cardstories_invitation .cardstories_pick .cardstories_cards');

    var invitation_picked = function() {
        //
        // the poll is not inhibited when a card has already been picked
        //
        $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
            equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
            equal(new_poll, undefined, 'poll_ignore metadata not set');
            $('.cardstories_card:nth(4)', element).click();
            $('#qunit-fixture .cardstories_invitation .cardstories_card_confirm_ok').click();
            start();
        };

        game.self[0] = picked;
        $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    };

    $.cardstories.
        invitation(player_id, game, $('#qunit-fixture .cardstories')).
        done(function(is_ready) {
            equal($('#qunit-fixture .cardstories_invitation .cardstories_pick.cardstories_active').length, 1);    
            equal($('#qunit-fixture .cardstories_invitation .cardstories_pick .cardstories_sentence').text(), sentence);
            equal($('.cardstories_card:nth(0) .cardstories_card_foreground', element).attr('src'), 'PATH/card0' + cards[0] + '.png');
            equal($('.cardstories_card:nth(5) .cardstories_card_foreground', element).attr('src'), 'PATH/card0' + cards[5] + '.png');
            $('.cardstories_card:nth(4)', element).click();
            $('#qunit-fixture .cardstories_invitation .cardstories_card_confirm_ok').click();

            window.setTimeout(invitation_picked, 50);
        });

});

test("invitation_participate", function() {
    setup();
    expect(11);

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

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
      equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
      equal(new_poll, undefined, 'poll_ignore metadata not set');
    };

    equal($('#qunit-fixture .cardstories_invitation .cardstories_participate.cardstories_active').length, 0);
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_invitation .cardstories_participate.cardstories_active').length, 1);
    equal($('#qunit-fixture .cardstories_participate .cardstories_sentence').text(), sentence);
    $('#qunit-fixture .cardstories_participate .cardstories_submit').click();
    $.cardstories.confirm_participate = false;
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    $.cardstories.confirm_participate = true;
});

test("widget invitation", function() {
    setup();
    expect(7);

    var player_id = 15;
    var game_id = 101;
    var sentence = 'SENTENCE';
    var modified = 4444;

    var ajax_poll = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=poll&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=game&game_id=' + game_id + '&player_id=' + player_id);
	var game = {
	    'id': game_id,
	    'state': 'invitation',
            'modified': modified,
	    'sentence': sentence
	};
        $.cardstories.ajax = ajax_poll;
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
    stop();
    expect(18);

    var player_id = 15;
    var game_id = 101;
    var picked = 2;
    var voted = 5;
    var board = [1,picked,3,4,voted];
    var sentence = 'SENTENCE';

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=vote&player_id=' + player_id + '&game_id=' + game_id + '&card=' + voted);
    };

    var game = {
	'id': game_id,
	'board': board,
	'self': [picked, null, [11,12,13,14,15,16,17]],
	'sentence': sentence
    };
    var element = $('#qunit-fixture .cardstories_vote .cardstories_voter');
    $('.cardstories_card:nth(0) .cardstories_card_foreground', element).attr('alt', 'SOMETHING');
    equal($('.cardstories_card:nth(1) .cardstories_card_foreground', element).attr('alt'), undefined);
    equal($('#qunit-fixture .cardstories_vote .cardstories_voter.cardstories_active').length, 0);

    var vote_voted = function() {
        //
        // the poll is not inhibited when a card has already been voted for
        //
        $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
            equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
            equal(new_poll, undefined, 'poll_ignore metadata not set');
            $('.cardstories_card:nth(4)', element).click();
            $('#qunit-fixture .cardstories_vote .cardstories_card_confirm_ok').click();
            start();
        };

        game.self[1] = voted;
        $.cardstories.vote(player_id, game, $('#qunit-fixture .cardstories'));
    };

    $.cardstories.
        vote(player_id, game, $('#qunit-fixture .cardstories')).
        done(function(is_ready) {
            equal($('#qunit-fixture .cardstories_vote .cardstories_voter.cardstories_active').length, 1);
            equal($('#qunit-fixture .cardstories_voter .cardstories_sentence').text(), sentence);
            for(var i = 0; i < board.length; i++) {
                equal($('.cardstories_card:nth(' + i + ') .cardstories_card_foreground', element).attr('src'), 'PATH/card0' + board[i] + '.png');
            }
            equal($('.cardstories_card:nth(0) .cardstories_card_foreground', element).attr('alt'), '', 'card0 alt was reset');
            equal($('.cardstories_card:nth(1) .cardstories_card_foreground', element).attr('alt'), 'My Card', 'card1 alt was set');
            equal($('.cardstories_card:nth(5) .cardstories_card_foreground', element).attr('src'), 'PATH/nocard.png');
            $('.cardstories_picked', element).click(); // must do nothing
            $('.cardstories_card:nth(4)', element).click();
            $('#qunit-fixture .cardstories_vote .cardstories_card_confirm_ok').click();

            window.setTimeout(vote_voted, 50);
        });
});

test("vote_viewer", function() {
    setup();
    expect(7);

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

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
      equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
      equal(new_poll, undefined, 'poll_ignore metadata not set');
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
    expect(8);

    var player_id = 15;
    var game_id = 101;

    var voter11 = 11;
    var voter12 = 12;
    var voter21 = 21;

    var board1 = 30;
    var board2 = 31;
    var board3 = 32;
    var board = [ board1, board2 ];

    var sentence = 'SENTENCE';

    var game = {
	'id': game_id,
	'owner': true,
        'sentence': sentence,
        'board': board,
        'players': [ [ voter11, board1, 'n', board3, [ ] ],
                     [ voter12, board2, 'n', board1, [ ] ],
                     [ voter21, board1, 'n', board2, [ ] ]
                   ],
	'ready': true
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=complete&owner_id=' + player_id + '&game_id=' + game_id);
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
      equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
      equal(new_poll, undefined, 'poll_ignore metadata not set');
    };

    equal($('#qunit-fixture .cardstories_vote .cardstories_owner.cardstories_active').length, 0);
    $.cardstories.vote(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_vote .cardstories_owner.cardstories_active').length, 1);

    var vote = $('#qunit-fixture .cardstories_vote .cardstories_owner');
    equal($('.cardstories_sentence', vote).text(), sentence);

    ok($('.cardstories_finish', vote).hasClass('cardstories_ready'), 'cardstories_ready');

    $('.cardstories_finish', vote).click();
});

test("complete", function() {
    setup();
    expect(3);

    var player_id = 15;
    var game_id = 101;

    var voter11 = 11;
    var voter12 = 12;
    var voter21 = 21;

    var board1 = 30;
    var board2 = 31;
    var board3 = 32;
    var board = [ board1, board2 ];

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
    $.cardstories.complete(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_complete.cardstories_active').length, 1);

    equal($('#qunit-fixture .cardstories_complete .cardstories_sentence').text(), sentence);
});

test("results_board", function() {
    setup();
    expect(19);

    var player_id = 15;
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

    var element = $('#qunit-fixture .cardstories_complete');
    $.cardstories.results_board(voter12, game, element);

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
    equal($('.cardstories_player_name', column).text(), voter12.toString());
    ok($('.cardstories_player_name', column).hasClass('cardstories_win'), 'cardstories_win');
    equal($('.cardstories_voter_name:nth(0)', column).text(), voter11.toString());
    ok($('.cardstories_voter_name:nth(0)', column).is(':visible'), 'col 1, first vote visible');
    equal($('.cardstories_voter_name:nth(1)', column).text(), voter21.toString());
    ok($('.cardstories_voter_name:nth(1)', column).is(':visible'), 'col 1, second vote visible');
    ok(!$('.cardstories_voter_name:nth(2)', column).is(':visible'), 'col 1, third vote hidden');

    column = $('.cardstories_column:nth(1)', element);
    equal($('.cardstories_card', column).metadata().card, board2);
    equal($('.cardstories_player_name', column).text(), voter21.toString());
    ok(!$('.cardstories_player_name', column).hasClass('cardstories_win'), 'cardstories_win not set');
    ok(!$('.cardstories_voter_name:nth(0)', column).is(':visible'), 'col 2, first vote hidden');
    
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

test("refresh_lobby", function() {
    setup();
    expect(15);

    var in_progress;
    var player_id = 10;
    var game1 = 100;
    var sentence1 = 'sentence1';
    var modified = 333;
    var games = {'games': [[game1, sentence1, 'invitation', 0]], 'win': {}, 'modified': modified };
    var root = $('#qunit-fixture .cardstories');

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=lobby&player_id=' + player_id + '&in_progress=' + in_progress.toString() + '&my=true');
	options.success(games);
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
      equal(ignored_request.modified, modified, 'poll_ignore request modified');
      equal(ignored_request.player_id, player_id, 'poll_ignore request player_id');
      equal(new_poll, undefined, 'poll_ignore metadata not set');
    };

    in_progress = true;
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 0, 'in_progress not active');
    $.cardstories.refresh_lobby(player_id, in_progress, true, root);
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 1, 'in_progress active');

    in_progress = false;
    equal($('#qunit-fixture .cardstories_lobby .cardstories_finished.cardstories_active').length, 0, 'finished not active');
    $.cardstories.refresh_lobby(player_id, in_progress, true, root);
    equal($('#qunit-fixture .cardstories_lobby .cardstories_finished.cardstories_active').length, 1, 'finished active');
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 0, 'in_progress not active');
  });

test("lobby_games", function() {
    setup();
    expect(24);

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
                 'win': {}
                };
    games.win[game1] = 'n';
    games.win[game2] = 'y';
    $.cardstories.lobby_games(player_id, games, $('#qunit-fixture .cardstories .cardstories_games_test'), $('#qunit-fixture .cardstories'));
    var element = $('#qunit-fixture .cardstories_games_test');
    // list of games
    ok($('.cardstories_games tbody tr:nth(0)', element).is(':visible'), 'first row is visible');
    ok($('.cardstories_games tbody tr:nth(1)', element).is(':visible'), 'second row is visible');
    equal($('.cardstories_games tbody tr', element).length, 2, 'only two rows visible');
    // check that the rows content match what is expected
    var first = $('.cardstories_games tbody tr:nth(0)', element);
    ok($('.cardstories_lobby_role', first).hasClass('cardstories_lobby_player'), 'role player');
    equal($('.cardstories_lobby_state', first).text(), 'invitation');
    equal($('.cardstories_lobby_win', first).text(), 'n');
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
    equal($('.cardstories_lobby_win', second).text(), 'y');
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
  });

test("poll_discard", function() {
    setup();
    expect(3);
    
    var root = $('#qunit-fixture .cardstories');
    $(root).metadata().poll = undefined;

    equal($.cardstories.poll_discard(root), undefined, 'noop on undefined');
    var poll = 1;
    $(root).metadata().poll = poll;
    equal($.cardstories.poll_discard(root), poll + 1, '++ to discard');
    equal($(root).metadata().poll, poll + 1, 'persists');
  });

test("start_story", function() {
    setup();
    expect(3);

    var player_id = 222;
    var root = $('#qunit-fixture .cardstories');

    var poll = 1;
    $(root).metadata().poll = poll;

    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 0, 'pick_card not active');
    $.cardstories.start_story(player_id, root);
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 1, 'pick_card active');
    equal($(root).metadata().poll, poll + 1);
  });

test("lobby_in_progress", function() {
    setup();
    expect(8);

    var player_id = 10;
    var game1 = 100;
    var sentence1 = 'sentence1';
    var games = {'games': [[game1, sentence1, 'invitation', 0]
                          ],
                 'win': {}
                };
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 0, 'in_progress not active');
    $.cardstories.lobby_in_progress(player_id, games, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 1, 'in_progress active');
    var element = $('#qunit-fixture .cardstories_in_progress');
    // lobby tab
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=lobby&player_id=' + player_id + '&in_progress=false&my=true');
    };
    $('.cardstories_tab', element).click();
    // list of games
    ok($('.cardstories_games tbody tr', element).length > 0, 'rows were inserted');
    // create game
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 0, 'pick_card not active');
    $('.cardstories_start_story', element).click();
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 0, 'in_progress not active');
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 1, 'pick_card active');
  });

test("lobby_finished", function() {
    setup();
    expect(8);

    var player_id = 10;
    var game1 = 100;
    var sentence1 = 'sentence1';
    var games = {'games': [[game1, sentence1, 'complete', 0]
                          ],
                 'win': {}
                };
    games.win[game1] = 'y';
    equal($('#qunit-fixture .cardstories_lobby .cardstories_finished.cardstories_active').length, 0, 'finished not active');
    $.cardstories.lobby_finished(player_id, games, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_lobby .cardstories_finished.cardstories_active').length, 1, 'finished active');
    var element = $('#qunit-fixture .cardstories_finished');
    // lobby tab
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=lobby&player_id=' + player_id + '&in_progress=true&my=true');
    };
    $('.cardstories_tab', element).click();
    // list of games
    ok($('.cardstories_games tbody tr', element).length > 0, 'rows were inserted');
    // create game
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 0, 'pick_card not active');
    $('.cardstories_start_story', element).click();
    equal($('#qunit-fixture .cardstories_lobby .cardstories_finished.cardstories_active').length, 0, 'finished not active');
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 1, 'pick_card active');
  });

test("poll", function() {
    setup();
    expect(18);
    
    var player_id = 11;
    var game_id = 222;
    var modified = 3333;

    var request = {'modified': modified, 'player_id': player_id, 'game_id': game_id};
    var root = $('#qunit-fixture .cardstories');

    //
    // lack of metadata inhibits the poll
    //
    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
      equal(new_poll, undefined, 'poll_ignore metadata not set');
    };
    equal($.cardstories.poll(request, root), false, 'poll metadata not set');

    //
    // successfull poll ends up redisplaying the page after retrieving its state
    //
    var game_ajax1 = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=game&game_id=' + game_id + '&player_id=' + player_id);
    };

    var poll_ajax1 = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=poll&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
        $.cardstories.ajax = game_ajax1;
	options.success(request);
    };

    $.cardstories.ajax = poll_ajax1;

    $(root).metadata().poll = 1;
    ok($.cardstories.poll(request, root), 'poll normal');

    //
    // if poll() is called before the previous poll() 
    // returned, the first poll answer will be trashed
    //
    var answer = {'answer': true};
    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
      equal(new_poll, old_poll + 1, 'poll increased');
      equal(request, ignored_request, 'ignored request');
      equal(answer, ignored_answer, 'ignored answer');
    };

    $.cardstories.ajax = function(options) {
        $.cardstories.poll_discard(root);
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=poll&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
	options.success(answer);
    };

    ok($.cardstories.poll(request, root), 'poll ignored');

    //
    // if poll() timesout, a new poll() request is sent
    //
    var poll_again = function(options) {
        equal(options.type, 'GET', 'poll again');
        equal(options.url, $.cardstories.url + '?action=poll&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET', 'poll timeout');
        equal(options.url, $.cardstories.url + '?action=poll&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
        $.cardstories.ajax = poll_again;
	options.success({'timeout': [modified+1111]});
    };

    ok($.cardstories.poll(request, root), 'poll timeout');
    
    $(root).metadata().poll = undefined;
  });

var stabilize = function(e, x, y) {
    var previous = 0;
    while(previous != $(e).height()) {
        previous = $(e).height();
        $(e).trigger({ type: 'mousemove', pageX: x, pageY: y});
    }
    return previous;
};

test("display_or_select_cards move", function() {
    setup();
    stop();
    expect(2);

    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_cards_hand', root);
    var onReady = function(is_ready) {
      var first = $('.cardstories_card:nth(1)', element);
      var offset = $(first).offset();
      var height = stabilize(first, offset.left, offset.top);
      var width = $(first).width();
      ok(stabilize(first, offset.left + width / 2, offset.top) > height, 'card is enlarged when moving toward the center');
      equal(stabilize(first, offset.left, offset.top), height, 'card is resized to the same size when the mouse goes back to the original position');
      start();
    };
    $.cardstories.
        display_or_select_cards([{'value':1},{'value':2},{'value':3},{'value':4},{'value':5},{'value':6}],
                                function() {}, 
                                element).
        done(onReady);
  });

test("display_or_select_cards select", function() {
    setup();
    stop();
    expect(6);

    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_cards_hand', root);
    var label = 'LABEL';
    var cards = [{'value':1},
                 {'value':2,'label':label},
                 {'value':3},
                 {'value':4},
                 {'value':5},
                 {'value':6}];
    var selected = 1;
    var onReady = function(is_ready) {
        var card_element = $('.cardstories_card', element).eq(1);
        equal($('.cardstories_card_foreground', card_element).attr('alt'), label);
        $('.cardstories_card', element).eq(selected).click();
    };
    var meta = $('.cardstories_card_template', element).metadata({type: "attr", name: "data"});
    var select = function(card, index, nudge, element) {
        equal(cards[index].value, card, 'selected card');
        var link = $('.cardstories_card', element).eq(index);
        var background = $('.cardstories_card_background', link);
        ok(link.hasClass('cardstories_card_selected'), 'link has class cardstories_card_selected');
        equal(background.attr('src'), meta.card_bg_selected);
        nudge();
        ok(!link.hasClass('cardstories_card_selected'), 'link no longer has class cardstories_card_selected');
        equal(background.attr('src'), meta.card_bg);
        start();
    };
    $.cardstories.
        display_or_select_cards(cards,
                                select, 
                                element).
        done(onReady);
  });

test("select_cards ok", function() {
    setup();
    stop();
    expect(2);

    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create', root);
    var confirm = $('.cardstories_card_confirm', element);
    var middle = confirm.metadata({type: "attr", name: "data"}).middle;
    var cards = [{'value':1},{'value':2},{'value':3},{'value':4},{'value':5},{'value':6}];
    var selected = 4;
    var onReady = function(is_ready) {
        $('.cardstories_card', element).eq(selected).click();
        $('.cardstories_card_confirm_ok', element).click();
    };
    var ok_callback = function(card) {
        equal(cards[selected].value, card, 'selected card');
        ok(confirm.hasClass('cardstories_card_confirm_right'), 'selected card is to the right of the middle position defined in the HTML meta data');
        start();
    };
    $.cardstories.
        select_cards(cards,
                     ok_callback, 
                     element).
        done(onReady);
  });

test("select_cards cancel", function() {
    setup();
    stop();
    expect(1);

    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create', root);
    var confirm = $('.cardstories_card_confirm', element);
    var middle = confirm.metadata({type: "attr", name: "data"}).middle;
    var cards = [{'value':1},{'value':2},{'value':3},{'value':4},{'value':5},{'value':6}];
    var selected = 4;
    var onReady = function(is_ready) {
        $('.cardstories_card', element).eq(selected).click();
        $('.cardstories_card_confirm_cancel', element).click();
        ok(true);
        start();
    };
    var ok_callback = function(card) {
        ok(false, 'ok_callback unexpectedly called');
    };
    $.cardstories.
        select_cards(cards,
                     ok_callback, 
                     element).
        done(onReady);
  });

test("create_deck", function() {
    setup();
    expect(15);
    var deck = $.cardstories.create_deck();
    equal(deck.length, 7);
    while(deck.length > 0) {
        var card = deck.pop();
        equal(typeof card, "number");
        equal(deck.indexOf(card), -1, 'duplicate of ' + card);
    }
  });
