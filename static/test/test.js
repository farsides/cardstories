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

var cardstories_default_reload = $.cardstories.reload;
var cardstories_default_setTimeout = $.cardstories.setTimeout;
var cardstories_default_ajax = $.cardstories.ajax;
var cardstories_original_error = $.cardstories.error;
var cardstories_original_poll_ignore = $.cardstories.poll_ignore;

function setup() {
    $.cardstories.setTimeout = function(cb, delay) { return window.setTimeout(cb, delay); };
    $.cardstories.ajax = function(o) { throw o; };
    $.cardstories.reload = $.cardstories.game_or_lobby;
    $.cardstories.confirm_participate = true;
    $.cardstories.poll_ignore = function() { throw 'poll_ignore'; };
    $.cardstories.error = cardstories_original_error;
}

test("error", function() {
    setup();
    expect(1);

    var alert = window.alert;
    window.alert = function(err) { equal(err, 'an error occurred', 'calls window.alert on error'); };
    $.cardstories.error('an error occurred');
    window.alert = alert;
  });

test("setTimeout", function() {
  expect(2);

  $.cardstories.setTimeout = cardstories_default_setTimeout;

  var setTimeout = $.cardstories.window.setTimeout;
  $.cardstories.window.setTimeout = function(cb, delay) {
    equal(cb, 'a function');
    equal(delay, 42);
  };

  $.cardstories.setTimeout('a function', 42);
  $.cardstories.window.setTimeout = setTimeout;
});

test("ajax", function() {
  expect(2);

  $.cardstories.ajax = cardstories_default_ajax;
  var ajax = jQuery.ajax;
  jQuery.ajax = function(options) {
    equal(options, 'some ajax options', 'calls jQuery.ajax with the supplied options');
    return 'some ajax result';
  };

  var result = $.cardstories.ajax('some ajax options');
  equal(result, 'some ajax result', 'returns the result of jQuery.ajax call');

  jQuery.ajax = ajax;
});

test("reload", function() {
    expect(4);

    var location = $.cardstories.location;
    var reload_link = $.cardstories.reload_link;
    $.cardstories.reload = cardstories_default_reload;
    $.cardstories.location = {search: ''};
    $.cardstories.reload_link = function(player_id, game_id, root) {
        equal(player_id, 11);
        equal(game_id, 101);
        equal(root, 'the root');
        return '?reload=link&';
    };

    $.cardstories.reload(11, 101, 'the root');
    equal($.cardstories.location.search, '?reload=link&');

    $.cardstories.location = location;
    $.cardstories.reload_link = reload_link;
});

test("xhr_error", function() {
    expect(1);

    $.cardstories.error = function(err) { equal(err, 'an xhr error occurred', 'calls $.cardstories.error'); };
    $.cardstories.xhr_error({xhr: 'object'}, 500, 'an xhr error occurred');
});

test("play_again_finish_state", function() {
    setup();
    expect(5);
    var player_id = 5;
	var game = {
	    'id': 7,
	    'state': 'fake_state',
	    'board': [],
	    'players': []
	};
	var root = $('#qunit-fixture .cardstories');
	game.owner = false;
    $.cardstories.complete(player_id, game, root);
    ok($('.play_again', root).is(':hidden'), 'Play again button is hidden when the player is owner');
	game.owner = true;
    $.cardstories.complete(player_id, game, root);
    ok(!$('.play_again', root).is(':hidden'), 'Play again button is visible when the player is owner');
    var create = $.cardstories.create;
    var send_game = $.cardstories.send_game;
    var $textarea = $('.cardstories_text', $('.cardstories_advertise', root));
    $.cookie('CARDSTORIES_INVITATIONS', null);
    $textarea.val('aaa@aaa.aaa\nbbb@bbb.bbb\nccc@ccc.ccc');
    var text = $textarea.val();
    $.cardstories.send_game = function () {}; //do nothing
    $.cardstories.advertise(player_id, game.id, root);
    $('.cardstories_submit', $('.cardstories_advertise', root)).click();
    $.cardstories.send_game = send_game;
    var inv_cookie = $.cookie('CARDSTORIES_INVITATIONS');
    $.cardstories.create = function (arg_player_id, arg_root) {
        equal(arg_player_id, player_id);
        equal(arg_root, root);
        $.cardstories.create = create;
    };
    $('.play_again', root).click();
    equal(text, inv_cookie);
});

test("permalink", function() {
    expect(2);
    equal($.cardstories.permalink(5), '?');
    equal($.cardstories.permalink(6, 7), '?game_id=7&');
});

test("reload_link", function() {
    expect(4);

    var player_id = 5;
    var game_id = 7;
    var _query = $.query;

    // Without player_id in the URL
    $.query = {
        'get': function(attr) { 
        }
    };
    equal($.cardstories.reload_link(player_id), '?');
    equal($.cardstories.reload_link(player_id, game_id), '?game_id=' + game_id + '&');

    // With player_id in the URL
    $.query = {
        'get': function(attr) { 
            if(attr == 'player_id') {
              return player_id;
            }
        }
    };
    equal($.cardstories.reload_link(player_id), '?player_id=' + player_id + '&');
    equal($.cardstories.reload_link(player_id, game_id), '?game_id=' + game_id + '&player_id=' + player_id + '&');

    $.query = _query;
  });

test("subscribe", function() {
    setup();
    expect(5);

    var player_id = 'player@test.com';
    var game_id = undefined;
    $.cookie('CARDSTORIES_ID', null);
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 0);
    $.cardstories.email(game_id, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 1);
    equal($.cookie('CARDSTORIES_ID'), null);
    $('#qunit-fixture .cardstories_subscribe .cardstories_email').val(player_id);
    // any ajax issued as indirect side effect of subscribing is ignored because it is
    // not a direct side effect
    $.cardstories.ajax = function(options) {};
    $('#qunit-fixture .cardstories_subscribe .cardstories_submit').submit();
    equal($.cookie('CARDSTORIES_ID').replace(/%40/g, "@"), player_id);
    $.cookie('CARDSTORIES_ID', null);
    equal($.cookie('CARDSTORIES_ID'), null);
});

test("subscribe_validation_error", function() {
    setup();
    expect(3);

    var player_id = 'PLAYER';
    var game_id = undefined;
    $.cookie('CARDSTORIES_ID', null);
    $.cardstories.email(game_id, $('#qunit-fixture .cardstories'));
    equal($.cookie('CARDSTORIES_ID'), null);
    $('#qunit-fixture .cardstories_subscribe .cardstories_email').val(player_id);
    // any ajax issued as indirect side effect of subscribing is ignored because it is
    // not a direct side effect
    $.cardstories.ajax = function(options) {};
    $('#qunit-fixture .cardstories_subscribe .cardstories_submit').submit();
    equal($('#qunit-fixture .cardstories_subscribe label.error').attr('for'), 'email');
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

test("test confirm_results_publication", function () {
    setup();
    expect(5);
    var player_id = 15;
    var game_id = 101;

    var root = $('#qunit-fixture .cardstories');
    root.addClass('cardstories_root');
    var vote_element = $('.cardstories_vote .cardstories_owner', root);
    var element = $('.cardstories_vote .cardstories_owner', '.cardstories_invitation');
    var query = 'action=complete&owner_id=' + player_id + '&game_id=' + game_id;
	var game = {
	    'id': game_id,
	    'state': 'fake_state'
	};
	var vote_owner = $.cardstories.vote_owner;

    $.cardstories.vote_owner = function (arg_player_id, arg_game, root) {
        equal(arg_player_id, player_id);
        equal(arg_game.id, game_id);
        ok($(root).hasClass('cardstories_root'), 'cardstories_root');
        $.cardstories.vote_owner = vote_owner;
    };

    var send_game = $.cardstories.send_game;
    $.cardstories.send_game = function (arg_player_id, arg_game_id) {
        equal(arg_player_id, player_id);
        equal(arg_game_id, game_id);
        $.cardstories.send_game = send_game;
    };

    $.cardstories.confirm_results_publication(player_id, game, root);
    $('.cardstories_notyet_announce_results').click();
    $('.cardstories_announce_results').click();
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

test("send_game on error", function() {
    setup();
    expect(1);

    var player_id = 15;
    var game_id = 101;

    $.cardstories.ajax = function(options) {
        var data = {error: 'error on send_game'};
        options.success(data);
    };

    $.cardstories.error = function(err) {
        equal(err, 'error on send_game', 'calls $.cardstories.error');
    };

    $.cardstories.send_game(player_id, game_id, $('#qunit-fixture .cardstories_create'), 'QUERY');
});

test("create", function() {
    setup();
    stop();
    expect(11);

    var player_id = 15;
    var game_id = 7;
    var card;
    var sentence = 'SENTENCE';

    $.cardstories.ajax = function(options) {
        equal(options.type, 'POST');
        equal(options.url, $.cardstories.url + '?action=create&owner_id=' + player_id + '&card=' + card);
	equal(options.data, 'sentence=' + sentence);

	var game = {
	    'game_id': game_id
	};
	options.success(game);
    };

    $.cardstories.reload = function(player_id2, game_id2, root2) {
        equal(player_id2, player_id);
        equal(game_id2, game_id);
        start();
    };

    var element = $('#qunit-fixture .cardstories_create');
    equal($('.cardstories_pick_card.cardstories_active', element).length, 0, 'pick_card not active');
    $.cardstories.
        create(player_id, $('#qunit-fixture .cardstories')).
        done(function(is_ready) {
            equal($('.cardstories_pick_card.cardstories_active', element).length, 1, 'pick_card active');
            equal($('.cardstories_write_sentence.cardstories_active', element).length, 0, 'sentence not active');
            var first_card = $('.cardstories_card:nth(0)', element);
            card = first_card.metadata({type: "attr", name: "data"}).card;
            first_card.click();
            $('.cardstories_card_confirm_ok', element).click();
            equal($('.cardstories_write_sentence.cardstories_active', element).length, 1, 'sentence active');
            ok($('.cardstories_sentence', element).attr('placeholder') !== undefined, 'placeholder is set');
            equal($('.cardstories_sentence', element).attr('placeholder'), $('.cardstories_sentence', element).val());
            $('.cardstories_write_sentence .cardstories_submit', element).submit();
            $('.cardstories_write_sentence .cardstories_sentence', element).val(sentence);
            $('.cardstories_write_sentence .cardstories_submit', element).submit();
        });
});

test("create on error", function() {
    setup();
    stop();
    expect(1);

    var player_id = 15;

    $.cardstories.ajax = function(options) {
        var data = {error: 'error on create'};
        options.success(data);
    };

    $.cardstories.error = function(err) {
        equal(err, 'error on create', 'calls $.cardstories.error');
    };

    var element = $('#qunit-fixture .cardstories_create');
    $.cardstories.
        create(player_id, $('#qunit-fixture .cardstories')).
        done(function(is_ready) {
            var first_card = $('.cardstories_card:nth(0)', element);
            first_card.click();
            $('.cardstories_card_confirm_ok', element).click();
            $('.cardstories_write_sentence .cardstories_sentence', element).val('SENTENCE');
            $('.cardstories_write_sentence .cardstories_submit', element).submit();
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
        equal(options.url, $.cardstories.url + '?action=state&type=lobby&modified=0&player_id=' + player_id + '&in_progress=true&my=true');
    };
    $('#qunit-fixture .cardstories').cardstories(player_id);
    ok($('#qunit-fixture .cardstories').hasClass('cardstories_root'), 'cardstories_root');
});

test("game", function() {
    setup();
    expect(5);

    var player_id = 15;
    var game_id = 101;
    var card = 1;
    var sentence = 'SENTENCE';
    var root = $('#qunit-fixture .cardstories');

    $.cardstories.fake_state = function(inner_player_id, game, element) {
	equal(inner_player_id, player_id);
	equal(game.id, game_id);
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=state&type=game&modified=0&game_id=' + game_id + '&player_id=' + player_id);
	var game = {
	    'id': game_id,
	    'state': 'fake_state'
	};
	options.success([game]);
    };

    $.cardstories.game(player_id, game_id, root);

    // Test link to lobby
    $.cardstories.reload = function(player_id2) {
        equal(player_id2, player_id);
    };
    $('.cardstories_go_lobby', root).click();
});

test("game on error", function() {
    setup();
    expect(1);

    $.cardstories.ajax = function(options) {
        var data = {error: 'error on game'};
        options.success(data);
    };

    $.cardstories.error = function(err) {
        equal(err, 'error on game', 'calls $.cardstories.error');
    };

    $.cardstories.game(11, 111, 'the root');
});

test("invitation_owner_invite_more", function() {
    setup();
    expect(5);

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
                     [ player2, null, 'n', null, [] ] ],
        'invited': [ player2 ]
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) { };
    $.cardstories.ajax = function(options) { };

    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 0);
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 1);
    $.cookie('CARDSTORIES_INVITATIONS', 'UNEXPECTED');
    $('#qunit-fixture .cardstories_invitation .cardstories_owner .cardstories_invite_friends').click();
    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 0);
    equal($('#qunit-fixture .cardstories_advertise .cardstories_text').val(), '');
    equal($('#qunit-fixture .cardstories_advertise.cardstories_active').length, 1);
});

test("invitation_owner_nobody_invited_yet", function() {
    setup();
    expect(3);

    var player1 = 'player1';
    var card1 = 5;
    var player_id = player1;
    var game_id = 101;

    var game = {
        'id': game_id,
        'owner': true,
        'ready': false,
        'players': [ [ player1, null, 'n', card1, [] ], [ 'player2', null, 'n', 10, [] ] ],
        'invited': [ ]
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) { };
    $.cardstories.ajax = function(options) { };

    equal($('#qunit-fixture .cardstories_advertise.cardstories_active').length, 0);
    // there is more than one player, therefore it is not mandatory to send invitations
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_advertise.cardstories_active').length, 0);
    // only the author is here and no pending invitations : show the advertise page
    game.players = [ game.players[0] ];
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_advertise.cardstories_active').length, 1);
});

test("invitation_owner", function() {
    setup();
    stop();
    expect(13);

    var player1 = 'player1';
    var card1 = 5;
    var player2 = 'player2';
    var player_id = player1;
    var game_id = 101;
    var sentence = 'SENTENCE';

    var game = {
	'id': game_id,
	'owner': true,
	'ready': true,
	'sentence': sentence,
        'players': [ [ player1, null, 'n', card1, [] ],
                     [ player2, null, 'n', null, [] ] ],
        'invited': [ player2 ]
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
            equal($('#qunit-fixture .cardstories_invitation .cardstories_owner .cardstories_sentence').text(), sentence);
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
    var owner = 150;
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
        'players': [
            [ owner, null, 'n', null, [] ],
            [ player_id, null, 'n', null, [] ]
        ],
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
            equal($('#qunit-fixture .cardstories_invitation .cardstories_pick .cardstories_sentence').text(), sentence); // invitation_board function side effect 
            equal($('.cardstories_card:nth(0) .cardstories_card_foreground', element).attr('src'), 'PATH/card0' + cards[0] + '.png');
            equal($('.cardstories_card:nth(5) .cardstories_card_foreground', element).attr('src'), 'PATH/card0' + cards[5] + '.png');
            $('.cardstories_card:nth(4)', element).click();
            $('#qunit-fixture .cardstories_invitation .cardstories_card_confirm_ok').click();

            window.setTimeout(invitation_picked, 50);
        });

});

test("invitation_pick_wait", function() {
    setup();
    expect(8);

    var player_id = 15;
    var owner = 150;
    var game_id = 101;
    var picked = 5;
    var cards = [1,2,3,4,picked,5];
    var sentence = 'SENTENCE';

    var game = {
	'id': game_id,
        'players': [
            [ owner, null, 'n', null, [] ],
            [ player_id, null, 'n', null, [] ]
        ],
	'self': [picked, null, cards],
	'sentence': sentence
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
        equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
        equal(new_poll, undefined, 'poll_ignore metadata not set');
    };

    var element = $('#qunit-fixture .cardstories_invitation .cardstories_pick_wait');
    equal($(element).hasClass('cardstories_active'), false, 'pick_wait not active');
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    equal($(element).hasClass('cardstories_active'), true, 'pick_wait active');
    equal($('.cardstories_sentence', element).text(), sentence);
    equal($('.cardstories_card', element).metadata().card, picked);
    var element_pick = $('#qunit-fixture .cardstories_invitation .cardstories_pick');
    equal($(element_pick).hasClass('cardstories_active'), false, 'pick not active');
    $('.cardstories_card_change', element).click();
    equal($(element_pick).hasClass('cardstories_active'), true, 'pick active');
});

test("invitation_anonymous", function() {
    setup();
    expect(2);

    var player_id = null;
    var game_id = 101;
    var sentence = 'SENTENCE';

    var _query = $.query;

    // Without player_id in the URL
    $.query = {
        'get': function(attr) {
            if (attr == "anonymous") {
                return "yes";
            }
        }
    };

    var owner = 'owner';
    var game = {
	'id': game_id,
        'players': [
            [ owner, null, 'n', null, [] ],
            [ 'player1', null, 'n', null, [] ],
            [ 'player2', null, 'n', null, [] ],
            [ 'player3', null, 'n', null, [] ],
            [ 'player4', null, 'n', null, [] ],
            [ 'player5', null, 'n', null, [] ]
        ],
        'owner_id': owner,
	'sentence': sentence
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
        equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
        equal(new_poll, undefined, 'poll_ignore metadata not set');
    };

    var element = $('#qunit-fixture .cardstories_invitation .cardstories_invitation_anonymous');
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));

    // Restore the original query
    $.query = _query;
});

test("invitation_board", function() {
    setup();
    expect(27);

    var player_id = null;
    var player1 = 'player1';
    var game_id = 101;
    var sentence = 'SENTENCE';

    var owner = 'owner';
    var game = {
	'id': game_id,
        'players': [
            [ owner, null, 'n', null, [] ],
            [ player1, null, 'n', null, [] ],
            [ 'player2', null, 'n', null, [] ],
            [ 'player3', null, 'n', null, [] ],
            [ 'player4', null, 'n', null, [] ],
            [ 'player5', null, 'n', null, [] ]
        ],
        'owner_id': owner,
	'sentence': sentence
    };

    var element = $('#qunit-fixture .cardstories_invitation .cardstories_board');
    $.cardstories.invitation_board(player_id, game, $('#qunit-fixture .cardstories'), element);
    equal($('.cardstories_sentence', element).text(), sentence);
    // anonymous view, all players present
    equal($('.cardstories_owner_seat .cardstories_player_name', element).text(), owner);
    for(var i = 1; i <= 5; i++) {
        equal($('.cardstories_player_seat_' + i + ' .cardstories_player_name', element).text(), 'player' + i);
    }
    // player view, all players present
    player_id = player1
    $.cardstories.invitation_board(player_id, game, $('#qunit-fixture .cardstories'), element);
    equal($('.cardstories_owner_seat .cardstories_player_name', element).text(), owner);
    equal($('.cardstories_player_seat_1 .cardstories_player_name', element).text(), 'player2');
    equal($('.cardstories_player_seat_2 .cardstories_player_name', element).text(), 'player3');
    equal($('.cardstories_player_seat_3 .cardstories_player_name', element).text(), 'player4');
    equal($('.cardstories_player_seat_4 .cardstories_player_name', element).text(), 'player5');
    equal($('.cardstories_player_seat_5 .cardstories_player_name', element).text(), 'player1');
    equal($('.cardstories_self_seat .cardstories_player_name', element).text(), 'player1');
    ok(!$('.cardstories_player_seat_4', element).hasClass('cardstories_empty_seat'), 'seat4 is not empty');
    // player view, one player missing
    game.players.pop();
    $.cardstories.invitation_board(player_id, game, $('#qunit-fixture .cardstories'), element);
    equal($('.cardstories_owner_seat .cardstories_player_name', element).text(), owner);
    ok(!$('.cardstories_owner_seat', element).hasClass('cardstories_empty_seat'), 'owner not empty seat');
    equal($('.cardstories_player_seat_1 .cardstories_player_name', element).text(), 'player2');
    ok(!$('.cardstories_player_seat_1', element).hasClass('cardstories_empty_seat'), 'seat1 not empty');
    equal($('.cardstories_player_seat_2 .cardstories_player_name', element).text(), 'player3');
    ok(!$('.cardstories_player_seat_2', element).hasClass('cardstories_empty_seat'), 'seat2 not empty');
    equal($('.cardstories_player_seat_3 .cardstories_player_name', element).text(), 'player4');
    ok(!$('.cardstories_player_seat_3', element).hasClass('cardstories_empty_seat'), 'seat3 not empty');
    equal($('.cardstories_player_seat_4 .cardstories_player_name', element).text(), 'player5');
    ok($('.cardstories_player_seat_4', element).hasClass('cardstories_empty_seat'), 'seat4 is empty');
    equal($('.cardstories_self_seat .cardstories_player_name', element).text(), 'player1');
    ok($('.cardstories_self_seat', element).hasClass('cardstories_self_seat'), 'self seat is not empty');
});

test("invitation_board_seat", function() {
    setup();
    expect(3);

    var player_id = 100;
    var card1 = 10;
    var card2 = 20;
    var card3 = 30;
    var game = {};

    var element = $('#qunit-fixture .cardstories_invitation .cardstories_board .cardstories_owner_seat');
    player = [ 'player1', card1, 'y', card3, [card1, card2] ]
    $.cardstories.invitation_board_seat(player_id, game, $('#qunit-fixture .cardstories'), element, player, 'owner');
    ok(element.hasClass('cardstories_player_picked'), 'picked');
    ok(element.hasClass('cardstories_player_voted'), 'voted');
    ok(element.hasClass('cardstories_player_won'), 'won');
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
        equal(options.url, $.cardstories.url + '?action=poll&type=game&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=state&type=game&modified=0&game_id=' + game_id + '&player_id=' + player_id);
	var game = {
	    'id': game_id,
	    'state': 'invitation',
            'modified': modified,
	    'sentence': sentence
	};
        $.cardstories.ajax = ajax_poll;
	options.success([game]);
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

test("invitation_voter_wait", function() {
    setup();
    expect(8);

    var player_id = 15;
    var game_id = 101;
    var picked = 5;
    var voted = 3;
    var board = [1,2,voted,4,picked,6];
    var sentence = 'SENTENCE';

    var game = {
	'id': game_id,
	'board': board,
	'self': [picked, voted, [picked,10,11,12,13,14]],
	'sentence': sentence
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
        equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
        equal(new_poll, undefined, 'poll_ignore metadata not set');
    };

    var element = $('#qunit-fixture .cardstories_vote .cardstories_voter_wait');
    equal($(element).hasClass('cardstories_active'), false, 'voter_wait not active');
    $.cardstories.vote(player_id, game, $('#qunit-fixture .cardstories'));
    equal($(element).hasClass('cardstories_active'), true, 'voter_wait active');
    equal($('.cardstories_sentence', element).text(), sentence);
    equal($('.cardstories_card', element).metadata().card, voted);
    var element_pick = $('#qunit-fixture .cardstories_vote .cardstories_voter');
    equal($(element_pick).hasClass('cardstories_active'), false, 'voter not active');
    $('.cardstories_card_change', element).click();
    equal($(element_pick).hasClass('cardstories_active'), true, 'voter active');
});

test("vote_anonymous", function() {
    setup();
    expect(3);

    var player_id = null;
    var game_id = 101;
    var picked = null;
    var voted = null;
    var board = [1,2,voted,4,picked,6];
    var sentence = 'SENTENCE';

    var _query = $.query;

    // Without player_id in the URL
    $.query = {
        'get': function(attr) {
            if (attr == "anonymous") {
                return "yes";
            }
        }
    };

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

    var element = $('#qunit-fixture .cardstories_vote .cardstories_vote_anonymous');
    $.cardstories.vote(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('.cardstories_sentence', element).text(), sentence);

    // Restore the original query
    $.query = _query;
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

    var root = $('#qunit-fixture .cardstories');

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
    var confirm_results_publication = $.cardstories.confirm_results_publication;
    $.cardstories.confirm_results_publication = function (arg_player_id, arg_game, arg_root, arg_vote_element) {
        equal(arg_player_id, player_id);
        equal(arg_game.id, game.id);
    };
    $('.cardstories_finish', vote).click();
    $.cardstories.confirm_results_publication = confirm_results_publication;
});

test("complete", function() {
    setup();
    expect(9);

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
    equal($('#qunit-fixture .cardstories_complete.cardstories_owner').length, 1, 'is owner');
    equal($('#qunit-fixture .cardstories_complete.cardstories_player').length, 0, 'is not player');
    game.owner = false;
    $.cardstories.complete(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_complete.cardstories_owner').length, 0, 'is not owner');
    equal($('#qunit-fixture .cardstories_complete.cardstories_player').length, 1, 'is player');

    equal($('#qunit-fixture .cardstories_complete.cardstories_why').length, 0, 'why is not set');
    $('#qunit-fixture .cardstories_complete .cardstories_set_why').click();
    equal($('#qunit-fixture .cardstories_complete.cardstories_why').length, 1, 'why is set');
    $('#qunit-fixture .cardstories_complete .cardstories_unset_why').click();
    equal($('#qunit-fixture .cardstories_complete.cardstories_why').length, 0, 'why is not set');
});

test("results_board", function() {
    setup();
    expect(24);

    var player_id = 15;
    var game_id = 101;

    var voter11 = 11;
    var voter12 = 12;
    var voter21 = 21;

    var board1 = 30;
    var board2 = 31;
    var board3 = 32;
    var board4 = 66; // a player that has been discarded when moving to voting phase
    var board = [ board1, board2, board3, board4 ];

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
    var winners = [voter11, voter12].join(', ');

    var element = $('#qunit-fixture .cardstories_complete');
    $.cardstories.results_board(voter12, game, element);

    equal($('.cardstories_winners', element).text(), winners);
    equal($('.cardstories_sentence', element).text(), sentence);
    
    var i;
    for(i = 0; i < board.length; i++) {
        equal($('.cardstories_column:nth(' + i + ')', element).css('display'), 'inline-block', 'column ' + i + ' is visible');
    }
    for(i = board.length; i < 6; i++) {
        equal(!$('.cardstories_column:nth(' + i + ')', element).css('display'), false, 'column ' + i + ' is not visible');
    }

    var column;
    column = $('.cardstories_column:nth(0)', element);
    equal($('.cardstories_card', column).metadata().card, board1);
    ok(column.hasClass('cardstories_winner_card'), 'winner card class');
    equal($('.cardstories_player_name', column).text(), voter12.toString());
    ok($('.cardstories_player_name', column).hasClass('cardstories_win'), 'cardstories_win');
    equal($('.cardstories_voter_name:nth(0)', column).text(), voter11.toString());
    equal($('.cardstories_voter_name:nth(0)', column).css('display'), 'block', 'col 1, first vote visible');
    equal($('.cardstories_voter_name:nth(1)', column).text(), voter21.toString());
    equal($('.cardstories_voter_name:nth(1)', column).css('display'), 'block', 'col 1, second vote visible');
    equal(!$('.cardstories_voter_name:nth(2)', column).css('display'), false, 'col 1, third vote hidden');

    column = $('.cardstories_column:nth(1)', element);
    equal($('.cardstories_card', column).metadata().card, board2);
    ok(!column.hasClass('cardstories_winner_card'), 'not winner card class');
    equal($('.cardstories_player_name', column).text(), voter21.toString());
    ok(!$('.cardstories_player_name', column).hasClass('cardstories_win'), 'cardstories_win not set');
    ok(!$('.cardstories_voter_name:nth(0)', column).is(':visible'), 'col 2, first vote hidden');
    
    // the player was discarded because he did not vote in time, the card has no name
    column = $('.cardstories_column:nth(3)', element);
    equal($('.cardstories_card', column).metadata().card, board4);
    equal($('.cardstories_player_name', column).text(), '');
  });

test("advertise", function() {
    setup();
    expect(8);
    
    var owner_id = 15;
    var game_id = 100;

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=invite&owner_id=' + owner_id + '&game_id=' + game_id + '&player_id=player1&player_id=player2');
    };

    var element = $('#qunit-fixture .cardstories_advertise');
    // the list of invitations is filled by the user
    $.cookie('CARDSTORIES_INVITATIONS', null);
    var text = " \n \t player1 \n\n   \nplayer2";
    $('.cardstories_text', element).text(text);
    $.cardstories.advertise(owner_id, game_id, $('#qunit-fixture .cardstories'));
    $('.cardstories_submit', element).click();
    equal($.cookie('CARDSTORIES_INVITATIONS'), text);

    // the list of invitations is retrieved from the cookie
    $('.cardstories_text', element).text('UNEXPECTED');
    $.cardstories.advertise(owner_id, game_id, $('#qunit-fixture .cardstories'));
    equal($('.cardstories_text', element).val(), text);

    $.cookie('CARDSTORIES_INVITATIONS', null);
    $('.cardstories_text', element).text('');
    $.cardstories.advertise(owner_id, game_id, $('#qunit-fixture .cardstories'));

    // button should be enabled only when text is not blank
    ok(!$('.cardstories_submit', element).hasClass('cardstories_submit_ready'), 'button should be disabled');
    $('.cardstories_text', element).text('player1').keyup();
    ok($('.cardstories_submit', element).hasClass('cardstories_submit_ready'), 'button should be enabled');

    // GAME_URL supplant
    var root = $('#qunit-fixture .cardstories');    
    var facebookUrl = $('#facebook_url').html().supplant({'GAME_URL': escape($.cardstories.permalink(owner_id, game_id, root))});
    var src = $('.cardstories_fb_invite', element).attr('src');
    ok(src.indexOf('GAME_URL') == -1, '{GAME_URL} supplant');
    equal(src, facebookUrl);
  });

test("refresh_lobby", function() {
    setup();
    expect(15);

    var in_progress;
    var my;
    var player_id = 10;
    var game1 = 100;
    var sentence1 = 'sentence1';
    var modified = 333;
    var games = {'games': [[game1, sentence1, 'invitation', 0]], 'win': {}, 'modified': modified };
    var root = $('#qunit-fixture .cardstories');

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=state&type=lobby&modified=0&player_id=' + player_id + '&in_progress=' + in_progress.toString() + '&my=' + my);
	options.success([games]);
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
      equal(ignored_request.modified, modified, 'poll_ignore request modified');
      equal(ignored_request.player_id, player_id, 'poll_ignore request player_id');
      equal(new_poll, undefined, 'poll_ignore metadata not set');
    };

    in_progress = true;
    my = true;
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 0, 'in_progress not active');
    $.cardstories.refresh_lobby(player_id, in_progress, my, root);
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 1, 'in_progress active');

    in_progress = false;
    my = false;
    equal($('#qunit-fixture .cardstories_lobby .cardstories_finished.cardstories_active').length, 0, 'finished not active');
    $.cardstories.refresh_lobby(player_id, in_progress, my, root);
    equal($('#qunit-fixture .cardstories_lobby .cardstories_finished.cardstories_active').length, 1, 'finished active');
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 0, 'in_progress not active');
});

test("refresh_lobby on error", function() {
    setup();
    expect(1);

    var root = $('#qunit-fixture .cardstories');

    $.cardstories.ajax = function(options) {
        var data = {error: 'error on refresh_lobby'};
        options.success(data);
    };

    $.cardstories.error = function(err) {
        equal(err, 'error on refresh_lobby', 'calls $.cardstories.error');
    };

    $.cardstories.refresh_lobby(42, true, true, root);
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
    equal($('.cardstories_games tbody tr:nth(0)', element).css('display'), 'table-row', 'first row is visible');
    equal($('.cardstories_games tbody tr:nth(1)', element).css('display'), 'table-row', 'second row is visible');
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
        equal(options.url, $.cardstories.url + '?action=state&type=game&modified=0&game_id=' + game1 + '&player_id=' + player_id);
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
        equal(options.url, $.cardstories.url + '?action=state&type=game&modified=0&game_id=' + game2 + '&player_id=' + player_id);
    };
    $('.cardstories_lobby_sentence', second).click();
    // modify the number row per page
    $('.cardstories_pager select', element).val(1);
    $('.cardstories_pager select', element).change();
    equal($('.cardstories_games tbody tr:nth(0) .cardstories_lobby_sentence', element).text(), sentence1);
    equal($('.cardstories_games tbody tr:nth(0)', element).css('display'), 'table-row', 'first row is visible');
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

test("lobby_games without games", function() {
    setup();
    expect(1);

    var player_id = 10;
    var games = {games: [], win: {}};
    var element = $('#qunit-fixture .cardstories .cardstories_games_test');
    $.cardstories.lobby_games(player_id, games, element, $('#qunit-fixture .cardstories'));
    equal($('.cardstories_pager', element).css('display'), 'none', 'pager is hidden');
});

test("create_write_sentence_animate", function() {
    setup();
    stop();
    expect(7);

    var player_id = 101;
    var card = 42;
    var root = $('#qunit-fixture .cardstories');
    var element = root.find('.cardstories_create .cardstories_write_sentence');

    var write_box = $('.cardstories_write', element);
    var card_shadow = $('.cardstories_card_shadow', element);
    var card_template = $('.cardstories_card_template', element);
    var card_imgs = $('img', card_template);
    var card_foreground = card_imgs.filter('.cardstories_card_foreground');

    var final_width = card_imgs.width();
    var starting_width = 220;

    $.cardstories.create_write_sentence_animate(player_id, card, element, root);

    equal(write_box.css('display'), 'none', 'write box is not visible initially');
    equal(card_shadow.css('display'), 'none', 'card shadow is not visible initially');
    ok(card_foreground.attr('src').match(/42/), 'src attribute is set properly to show the chosen card');
    equal(card_imgs.width(), 220, 'card starts out at 220px wide');

    var interval = setInterval(function() {
        if (write_box.css('display') === 'block') {
            equal(write_box.css('display'), 'block', 'write box is visible after animation');
            equal(card_shadow.css('display'), 'block', 'card shadow is visible after animation');
            equal(card_imgs.width(), final_width, 'after animation card grows to its original width');
            clearInterval(interval);
            start();
        }
    }, 750);
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

test("poll_ignore", function() {
    $.cardstories.poll_ignore = cardstories_original_poll_ignore;

    if (console && console.log) {
        expect(2);

        var log = console.log;

        console.log = function(text) {
            equal(text, 'poll ignored because 42 higher than 24');
        };
        $.cardstories.poll_ignore('req', 'answer', 42, 24);

        console.log = function(text) {
            equal(text, 'poll ignored because metadata is not set');
        };
        $.cardstories.poll_ignore('req', 'answer', undefined, 42);

        console.log = log;
    }
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
    expect(10);

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
        equal(options.url, $.cardstories.url + '?action=state&type=lobby&modified=0&player_id=' + player_id + '&in_progress=false&my=true');
    };
    $('.cardstories_tab_finished', element).click();
    // list of games
    ok($('.cardstories_games tbody tr', element).length > 0, 'rows were inserted');
    // create game
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 0, 'pick_card not active');
    $('.cardstories_start_story', element).click();
    equal($('#qunit-fixture .cardstories_lobby .cardstories_in_progress.cardstories_active').length, 0, 'in_progress not active');
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 1, 'pick_card active');
    // solo mode
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=solo&player_id=' + player_id);
    };
    $('.cardstories_solo', element).click();
  });

test("lobby_finished", function() {
    setup();
    expect(10);

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
        equal(options.url, $.cardstories.url + '?action=state&type=lobby&modified=0&player_id=' + player_id + '&in_progress=true&my=true');
    };
    $('.cardstories_tab_in_progress', element).click();
    // list of games
    ok($('.cardstories_games tbody tr', element).length > 0, 'rows were inserted');
    // create game
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 0, 'pick_card not active');
    $('.cardstories_start_story', element).click();
    equal($('#qunit-fixture .cardstories_lobby .cardstories_finished.cardstories_active').length, 0, 'finished not active');
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 1, 'pick_card active');
    // solo mode
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=solo&player_id=' + player_id);
    };
    $('.cardstories_solo', element).click();
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
        equal(options.url, $.cardstories.url + '?action=state&type=game&modified=0&game_id=' + game_id + '&player_id=' + player_id);
    };

    var poll_ajax1 = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=poll&type=game&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
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
        equal(options.url, $.cardstories.url + '?action=poll&type=game&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
	options.success(answer);
    };

    ok($.cardstories.poll(request, root), 'poll ignored');

    //
    // if poll() timesout, a new poll() request is sent
    //
    var poll_again = function(options) {
        equal(options.type, 'GET', 'poll again');
        equal(options.url, $.cardstories.url + '?action=poll&type=game&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET', 'poll timeout');
        equal(options.url, $.cardstories.url + '?action=poll&type=game&modified=' + modified + '&player_id=' + player_id + '&game_id=' + game_id);
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
    root.addClass('cardstories_root');
    $('.cardstories_create .cardstories_pick_card .cardstories_cards', root).show();
    $.cardstories.set_active(root, $('.cardstories_create .cardstories_pick_card', root));
    var element = $('.cardstories_create .cardstories_pick_card .cardstories_cards_hand', root);
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
        display_or_select_cards('move',
                                [{'value':1},{'value':2},{'value':3},{'value':4},{'value':5},{'value':6}],
                                function() {}, 
                                element).
        done(onReady);
  });

test("display_or_select_cards select", function() {
    setup();
    stop();
    expect(9);

    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_cards_hand', root);
    var label = 'LABEL';
    var cards = [{'value':1},
                 {'value':2,'label':label},
                 {'value':3,'inactive':true},
                 {'value':4},
                 {'value':5},
                 {'value':6}];
    var selected = 1;
    var inactive = 2;
    var zindex;
    var onReady = function(is_ready) {
        var card_element = $('.cardstories_card', element).eq(1);
        var foreground = $('.cardstories_card_foreground', card_element);
        equal(foreground.attr('alt'), label);
        zindex = card_element.css('z-index');
        ok($('.cardstories_card', element).eq(inactive).hasClass('cardstories_card_inactive'), 'inactive class');
        $('.cardstories_card', element).eq(inactive).click(); // noop
        $('.cardstories_card', element).eq(selected).click();
    };
    var meta = $('.cardstories_card_template', element).metadata({type: "attr", name: "data"});
    var select = function(card, index, nudge, element) {
        equal(cards[index].value, card, 'selected card');
        var link = $('.cardstories_card', element).eq(index);
        var background = $('.cardstories_card_background', link);
        ok(link.hasClass('cardstories_card_selected'), 'link has class cardstories_card_selected');
        equal(link.css('z-index'), '200');
        equal(background.attr('src'), meta.card_bg_selected);
        nudge();
        ok(!link.hasClass('cardstories_card_selected'), 'link no longer has class cardstories_card_selected');
        equal(background.attr('src'), meta.card_bg);
        equal(link.css('z-index'), zindex);
        start();
    };
    $.cardstories.
        display_or_select_cards('select',
                                cards,
                                select, 
                                element).
        done(onReady);
  });

test("display_or_select_cards select no bg", function() {
    setup();
    stop();
    expect(4);

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
        var background = $('.cardstories_card .cardstories_card_background', element).eq(1);
        equal(background.attr('src'), undefined);
        $('.cardstories_card', element).eq(selected).click();
    };
    var meta = $('.cardstories_card_template', element).metadata({type: "attr", name: "data"});
    var select = function(card, index, nudge, element) {
        var link = $('.cardstories_card', element).eq(index);
        var background = $('.cardstories_card_background', link);
        equal(background.attr('src'), meta.card_bg_selected);
        nudge();
        equal(background.attr('src'), undefined);
        start();
    };
    var background = $('.cardstories_card_template .cardstories_card_background', element);
    equal(background.attr('src'), 'templatebackground');
    meta.card_bg = '';
    $.cardstories.
        display_or_select_cards('select no bg',
                                cards,
                                select, 
                                element).
        done(onReady);
  });

test("display_or_select_cards twice", function() {
    setup();
    stop();
    expect(2);

    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_cards_hand', root);
    var label = 'LABEL';
    var card1 = 11;
    var create_cards = function(card) {
        return [
            {'value':card},
            {'value':2,'label':label},
            {'value':3},
            {'value':4},
            {'value':5},
            {'value':6}];
    };

    var meta = $('.cardstories_card_template', element).metadata({type: "attr", name: "data"});
    var check = function(is_ready) {
        var foreground = $('.cardstories_card .cardstories_card_foreground', element).eq(0);
        equal(foreground.attr('src'), meta.card.supplant({'card': card1}));
    };
    $.cardstories.
        display_or_select_cards('twice',
                                create_cards(card1),
                                undefined, 
                                element).
        done(function(is_ready) {
            check(is_ready);
            card1 = 22;
            $.cardstories.
                display_or_select_cards('twice',
                                        create_cards(card1),
                                        undefined, 
                                        element).
                done(function(is_ready) {
                    check(is_ready);
                    start();
                });
        });
  });

test("select_cards ok", function() {
    setup();
    stop();
    expect(2);

    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_pick_card', root);
    $.cardstories.set_active(root, element);
    var confirm = $('.cardstories_card_confirm', element);
    var middle = confirm.metadata({type: "attr", name: "data"}).middle;
    var cards = [{'value':1},{'value':2},{'value':3},{'value':4},{'value':5},{'value':6}];
    var selected = 5;
    var onReady = function(is_ready) {
        $('.cardstories_card', element).eq(selected).click();
        $('.cardstories_card_confirm_ok', element).click();
    };
    var ok_callback = function(card) {
        equal(cards[selected].value, card, 'selected card');
        ok(element.hasClass('cardstories_card_confirm_right'), 'selected card is to the right of the middle position defined in the HTML meta data');
        start();
    };
    $.cardstories.
        select_cards('ok',
                     cards,
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
        select_cards('cancel',
                     cards,
                     ok_callback, 
                     element).
        done(onReady);
  });

test("select_cards single", function() {
    setup();
    expect(6);
    stop();

    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_cards_hand', root);
    var onReady = function(is_ready) {
        var links = $('a.cardstories_card', element);
        links.each(function(index) {
            $(this).click();
            var tmp = index === 0;
            var condition = $(this).hasClass('cardstories_card_selected') == tmp;
            var not = $(this).hasClass('cardstories_card_selected') ? '' : 'not';
            ok(condition, 'Card ' + index + ' ' + not +  ' picked.');
        });
        start();
    };
    $.cardstories.
        display_or_select_cards('single',
                                [{'value':1},{'value':2},{'value':3},{'value':4},{'value':5},{'value':6}],
                                function() {},
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

test("credits", function() {
    setup();
    expect(4);

    var root = $('#qunit-fixture .cardstories');
    var long = $('.cardstories_credits_long', root);
    equal(long.is(':visible'), false, 'credits not visible');
    $.cardstories.credits(root);
    $('.cardstories_credits_short', root).click();
    equal(long.is(':visible'), true, 'credits visible');
    equal($('.jspArrowUp', long).css('background-image').indexOf('url('), 0, 'up arrow for scrolling');
    $('.cardstories_credits_close', long).click();
    equal(long.is(':visible'), false, 'credits not visible');
  });

test("solo", function() {
    setup();
    expect(2);

    var root = $('#qunit-fixture .cardstories');
    var player_id = 15;
    var game_id = 7;

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=solo&player_id=' + player_id);

	var game = {
	    'game_id': game_id
	};
	options.success(game);
    };

    $.cardstories.reload = function(player_id2, game_id2, root2) {
        equal(player_id2, player_id);
        equal(game_id2, game_id);
        start();
    };

    $.cardstories.solo(player_id, root);
});

test("solo on error", function() {
    setup();
    expect(1);

    var root = $('#qunit-fixture .cardstories');
    var player_id = 15;

    $.cardstories.ajax = function(options) {
        var data = {error: 'error on solo'};
	options.success(data);
    };

    $.cardstories.error = function(err) {
        equal(err, 'error on solo', 'calls $.cardstories.error');
    };

    $.cardstories.solo(player_id, root);
});

test("poll on error", function() {
    setup();
    expect(1);

    var root = $('#qunit-fixture .cardstories');
    root.metadata().poll = 1;

    $.cardstories.ajax = function(options) {
        var data = {error: 'error on poll'};
	options.success(data);
    };

    $.cardstories.error = function(err) {
        equal(err, 'error on poll', 'calls $.cardstories.error');
    };

    $.cardstories.poll({}, root);
});

test("trigger_keypress, trigger_keydown helpers", function() {
    expect(4);

    var key_code = 101;
    var trigger = $.event.trigger;

    $.event.trigger = function(options) {
        equal(options.type, 'keypress');
        equal(options.which, key_code);
    };

    $('#qunit-fixture').trigger_keypress(key_code);
    $('#qunit-fixture').trigger_keydown(key_code);

    $.event.trigger = trigger;
});

test("onbeforeunload", function() {
    setup();
    expect(1);

    $(window).trigger('beforeunload');
    equal($.cardstories.error, $.cardstories.noop, 'error handler gets set to a noop function on beforeunload');
});
