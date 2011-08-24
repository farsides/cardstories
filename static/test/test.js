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

$.fx.off = true;

var cardstories_default_reload = $.cardstories.reload;
var cardstories_default_setTimeout = $.cardstories.setTimeout;
var cardstories_default_delay = $.cardstories.delay;
var cardstories_default_ajax = $.cardstories.ajax;
var cardstories_default_error = $.cardstories.error;
var cardstories_default_poll_ignore = $.cardstories.poll_ignore;
var cardstories_default_create_write_sentence = $.cardstories.create_write_sentence;
var cardstories_default_animate_sprite = $.cardstories.animate_sprite;

function setup() {
    $.cardstories.setTimeout = function(cb, delay) { return window.setTimeout(cb, 0); };
    $.cardstories.delay = function(o, delay, qname) { return; };
    $.cardstories.ajax = function(o) { throw o; };
    $.cardstories.reload = $.cardstories.game_or_lobby;
    $.cardstories.confirm_participate = true;
    $.cardstories.poll_ignore = function() { throw 'poll_ignore'; };
    $.cardstories.error = cardstories_default_error;
    $.cardstories.create_write_sentence = cardstories_default_create_write_sentence;
    $.cardstories.animate_sprite = function(movie, fps, frames, cb) { movie.show(); cb(); };
    $.cardstories.preload_images_helper = function(root, cb) { cb(); };
}

module("cardstories", {setup: setup});

test("error", 1, function() {
    var alert = window.alert;
    window.alert = function(err) { equal(err, 'an error occurred', 'calls window.alert on error'); };
    $.cardstories.error('an error occurred');
    window.alert = alert;
});

test("setTimeout", 2, function() {
    $.cardstories.setTimeout = cardstories_default_setTimeout;

    var setTimeout = $.cardstories.window.setTimeout;
    $.cardstories.window.setTimeout = function(cb, delay) {
      equal(cb, 'a function');
      equal(delay, 42);
    };

    $.cardstories.setTimeout('a function', 42);
    $.cardstories.window.setTimeout = setTimeout;
});

asyncTest("delay", 1, function() {
    $.cardstories.delay = cardstories_default_delay;
    var starttime = new Date();
    var q = $({});
    $.cardstories.delay(q, 100, 'chain');
    q.queue('chain', function() {
        var endtime = new Date();
        elapsed = endtime.getTime() - starttime.getTime();
        ok(elapsed > 50, 'elapsed time');
        start();
    });
    q.dequeue('chain');
});

test("ajax", 2, function() {
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

test("reload", 4, function() {
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

test("xhr_error", 1, function() {
    $.cardstories.error = function(err) { equal(err, 'an xhr error occurred', 'calls $.cardstories.error'); };
    $.cardstories.xhr_error({xhr: 'object'}, 500, 'an xhr error occurred');
});

test("permalink", 2, function() {
    equal($.cardstories.permalink(5), '?');
    equal($.cardstories.permalink(6, 7), '?game_id=7&');
});

test("reload_link", 4, function() {
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

asyncTest("notify_active", 1, function() {
    var skin = 'email';
    var root = $('#qunit-fixture .cardstories');

    root.bind('active.cardstories', function(e, state) {
        equal(state, skin);
        start();
    });

    $.cardstories.notify_active(root, skin);
});

test("display_progress_bar", 14, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_write_sentence', root);
    var pbar = $('.cardstories_progress', element);
    var step = 2;

    $.cardstories.display_progress_bar(step, element, root);
    ok($('.cardstories_step1', pbar).hasClass('old'), 'step 1 has old class');
    ok($('.cardstories_step2', pbar).hasClass('selected'), 'step 2 is selected');
    equal($('.cardstories_step3', pbar).attr('class'), 'cardstories_step3', 'step 3 is bare');
    equal($('.cardstories_step4', pbar).attr('class'), 'cardstories_step4', 'step 4 is bare');
    equal($('.cardstories_step5', pbar).attr('class'), 'cardstories_step5', 'step 5 is bare');
    equal($('.cardstories_step6', pbar).attr('class'), 'cardstories_step6', 'step 6 is bare');
    equal(pbar.data('step'), step, 'step was saved');

    // Should do nothing a second time.
    $.cardstories.display_progress_bar(4, element, root);
    ok($('.cardstories_step1', pbar).hasClass('old'), 'step 1 has old class');
    ok($('.cardstories_step2', pbar).hasClass('selected'), 'step 2 is selected');
    equal($('.cardstories_step3', pbar).attr('class'), 'cardstories_step3', 'step 3 is bare');
    equal($('.cardstories_step4', pbar).attr('class'), 'cardstories_step4', 'step 4 is bare');
    equal($('.cardstories_step5', pbar).attr('class'), 'cardstories_step5', 'step 5 is bare');
    equal($('.cardstories_step6', pbar).attr('class'), 'cardstories_step6', 'step 6 is bare');
    equal(pbar.data('step'), step, 'step was saved');
});

test("display_owner_nick", 1, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create', root);
    var name = 'Bogus Name';

    $.cardstories.display_owner_nick(name, element);

    equal($('.cardstories_nickname', element).html(), name, 'Name was properly set.');
});

asyncTest("display_modal", 2, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create', root);
    var modal = $('.cardstories_info', element);
    var overlay = $('.cardstories_modal_overlay', element);

    $.cardstories.display_modal(modal, overlay, function () {
        equal(overlay.css('display'), 'block', 'modal overlay is on');
        modal.find('a').click();
        equal(overlay.css('display'), 'none', 'modal overlay is off');
        start();
    });
});

asyncTest("animate_progress_bar", 14, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_pick_card', root);
    var progress = $('.cardstories_progress', element);
    var cur = 1;
    var step = 4;

    $.cardstories.display_progress_bar(cur, element, root);

    var dst_mark = $('<div>')
                    .addClass('cardstories_progress_mark')
                    .addClass('cardstories_progress_mark' + step)
                    .appendTo(progress);
    var final_left = dst_mark.position().left;
    dst_mark.remove();

    ok($('.cardstories_step1', progress).hasClass('selected'), 'step 1 is selected');
    equal($('.cardstories_step2', progress).attr('class'), 'cardstories_step2', 'step 2 is bare');
    equal($('.cardstories_step3', progress).attr('class'), 'cardstories_step3', 'step 3 is bare');
    equal($('.cardstories_step4', progress).attr('class'), 'cardstories_step4', 'step 4 is bare');
    equal($('.cardstories_step5', progress).attr('class'), 'cardstories_step5', 'step 5 is bare');
    equal($('.cardstories_step6', progress).attr('class'), 'cardstories_step6', 'step 6 is bare');
    $.cardstories.animate_progress_bar(step, element, function() {
        equal($('.cardstories_progress_mark', progress).position().left, final_left, 'mark is at final position');
        ok($('.cardstories_step1', progress).hasClass('old'), 'step 1 is old');
        ok($('.cardstories_step2', progress).hasClass('old'), 'step 2 is old');
        ok($('.cardstories_step3', progress).hasClass('old'), 'step 3 is old');
        ok($('.cardstories_step4', progress).hasClass('selected'), 'step 4 is selected');
        equal($('.cardstories_step5', progress).attr('class'), 'cardstories_step5', 'step 5 is bare');
        equal($('.cardstories_step6', progress).attr('class'), 'cardstories_step6', 'step 6 is bare');
        equal(progress.data('step'), step, 'step was saved');
        start();
    });
});

asyncTest("animate_scale", 7, function() {
    var element = $('#qunit-fixture .cardstories .cardstories_create');
    var el = $('.cardstories_info', element);
    
    // Grab initial position.
    element.show();
    el.show();
    var orig_top = el.position().top;
    var orig_left = el.position().left;
    var orig_width = el.width();
    var orig_height = el.height();
    var orig_fontsize = parseInt(el.css('font-size'), 10);
    el.hide();

    var factor = 5;
    var duration = 500;

    equal(el.css('display'), 'none', 'Element starts hidden');
    $.cardstories.animate_scale(false, factor, duration, el, function () {
        equal(el.css('display'), 'block', 'Element is visible after animation.');
        equal(el.position().top, orig_top, 'Element achieves proper top.');
        equal(el.position().left, orig_left, 'Element achieves proper left.');
        equal(el.width(), orig_width, 'Element achieves proper width.');
        equal(el.height(), orig_height, 'Element achieves proper height.');
        equal(parseInt(el.css('font-size'), 10), orig_fontsize, 'Element achieves proper font size.');
        start();
    });
});

asyncTest("animate_scale reverse", 7, function() {
    var element = $('#qunit-fixture .cardstories .cardstories_create');
    // Make sure the element and its ancestors are visible,
    // to prevent some versions of FF report faulty values.
    var el = $('.cardstories_info', element).show();
    el.parents().show();
    var orig_top = parseInt(el.css('top'), 10);
    var orig_left = parseInt(el.css('left'), 10);
    var orig_width = el.width();
    var orig_height = el.height();
    var orig_fontsize = parseInt(el.css('font-size'), 10);

    var factor = 5;
    var duration = 500;

    var dst_width = Math.floor(orig_width / factor);
    var dst_height = Math.floor(orig_height / factor);
    var dst_top = orig_top + Math.floor((orig_height - dst_height)/2);
    var dst_left = orig_left + Math.floor((orig_width - dst_width)/2);
    var dst_fontsize = Math.floor(orig_fontsize / factor);

    el.show();
    equal(el.css('display'), 'block', 'Element starts visible');
    $.cardstories.animate_scale(true, factor, duration, el, function () {
        equal(el.css('display'), 'none', 'Element is invisible after animation.');
        // Show the element, otherwise some versions of FF report faulty values.
        el.show();
        equal(parseInt(el.css('top'), 10), orig_top, 'Element achieves proper top.');
        equal(parseInt(el.css('left'), 10), orig_left, 'Element achieves proper left.');
        equal(el.width(), orig_width, 'Element achieves proper width.');
        equal(el.height(), orig_height, 'Element achieves proper height.');
        equal(parseInt(el.css('font-size'), 10), orig_fontsize, 'Element achieves proper font size.');
        start();
    });
});

asyncTest("animate_sprite", 3, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_invitation .cardstories_owner', root);
    var movie = $('#cardstories_player_join_1', element);
    var frames = 18;

    equal(movie.css('display'), 'none', 'movie starts hidden');

    // IE does not use 'background-position', but 'background-position-x'.
    if (movie.css('background-position') !== undefined) {
        equal(movie.css('background-position'), '0% 0%', 'movie starts at 0% background position');
    } else {
        equal(movie.css('background-position-x'), 'left', 'movie starts at 0% background position');
    }

    $.cardstories.animate_sprite = cardstories_default_animate_sprite;
    $.cardstories.animate_sprite(movie, frames, frames, function() {
        if (movie.css('background-position') !== undefined) {
            notEqual(movie.css('background-position'), '0% 0%', 'movie is no longer at 0% background position');
        } else {
            notEqual(movie.css('background-position-x'), 'left', 'movie is no longer at 0% background position');
        }
        start();
    });
});

test("subscribe", 6, function() {
    var player_id = 'player@test.com';
    var game_id = undefined;
    $.cookie('CARDSTORIES_ID', null);
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 0);
    $.cardstories.email(game_id, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 1);
    equal($.cookie('CARDSTORIES_ID'), null);
    $('#qunit-fixture .cardstories_subscribe .cardstories_email').val(player_id);
    var called = false;
    // any ajax issued as indirect side effect of subscribing is ignored because it is
    // not a direct side effect
    $.cardstories.ajax = function(options) {
        called = true;
    };
    $('#qunit-fixture .cardstories_subscribe .cardstories_emailform').submit();
    ok(called, 'ajax function called, hence input validated');
    equal($.cookie('CARDSTORIES_ID').replace(/%40/g, "@"), player_id);
    $.cookie('CARDSTORIES_ID', null);
    equal($.cookie('CARDSTORIES_ID'), null);
});

test("widget subscribe", 3, function() {
    equal($.cookie('CARDSTORIES_ID'), null);
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 0);
    $('#qunit-fixture .cardstories').cardstories(undefined, undefined);
    equal($('#qunit-fixture .cardstories_subscribe.cardstories_active').length, 1);
});

test("welcome_url", 1, function() {
    var location = $.cardstories.location;
    var welcome_url = '/';
    $.cookie('CARDSTORIES_WELCOME', welcome_url);
    $.cardstories.location = {href: 'http://fake.href'};
    $('#qunit-fixture .cardstories').cardstories(undefined, undefined);
    equal($.cardstories.location.href, welcome_url);
    $.cardstories.location = location;
    $.cookie('CARDSTORIES_WELCOME', null);
});

asyncTest("send_game", 5, function() {
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

test("send_game on error", 1, function() {
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

asyncTest("create", 16, function() {
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

    $.cardstories.create_write_sentence = function(player_id, card_value, root) {
        cardstories_default_create_write_sentence.call($.cardstories, player_id, card_value, root);
        equal($('.cardstories_write_sentence.cardstories_active', element).length, 1, 'sentence active');
        ok($('.cardstories_sentence', element).attr('placeholder') !== undefined, 'placeholder is set');
        equal($('.cardstories_sentence', element).attr('placeholder'), $('.cardstories_sentence', element).val());
        equal($('.cardstories_write_sentence .cardstories_submit', element).css('display'), 'none', 'OK button is initially hidden');
        $('.cardstories_write_sentence .cardstories_submit', element).submit();
        $('.cardstories_write_sentence .cardstories_sentence', element).val('o').change();
        equal($('.cardstories_write_sentence .cardstories_submit', element).css('display'), 'none', 'OK button is hidden if text is too short');
        $('.cardstories_write_sentence .cardstories_sentence', element).val(sentence).change();
        ok($('.cardstories_write_sentence .cardstories_submit', element).css('display') !== 'none', 'OK button is visible if valid text has been set');
        $('.cardstories_write_sentence .cardstories_submit', element).submit();
    };

    var element = $('#qunit-fixture .cardstories_create');
    equal($('.cardstories_pick_card.cardstories_active', element).length, 0, 'pick_card not active');
    $.cardstories.
        create(player_id, $('#qunit-fixture .cardstories')).
        done(function() {
            equal($('.cardstories_modal_overlay', element).css('display'), 'block', 'modal overlay is on');
            var a = $('.cardstories_info', element).find('a').click();
            equal($('.cardstories_modal_overlay', element).css('display'), 'none', 'modal overlay is off');
            equal($('.cardstories_pick_card.cardstories_active', element).length, 1, 'pick_card active');
            equal($('.cardstories_write_sentence.cardstories_active', element).length, 0, 'sentence not active');
            var first_card = $('.cardstories_cards_hand .cardstories_card:nth(0)', element);
            card = first_card.metadata({type: "attr", name: "data"}).card;
            first_card.click();
            $('.cardstories_card_confirm_ok', element).find('a').click();
        });
});

asyncTest("create on error", 1, function() {
    var player_id = 15;

    $.cardstories.ajax = function(options) {
        var data = {error: 'error on create'};
        options.success(data);
    };

    $.cardstories.error = function(err) {
        equal(err, 'error on create', 'calls $.cardstories.error');
        start();
    };

    var element = $('#qunit-fixture .cardstories_create');

    $.cardstories.create_write_sentence = function(player_id, card_value, root) {
        cardstories_default_create_write_sentence.call($.cardstories, player_id, card_value, root);
        $('.cardstories_write_sentence .cardstories_sentence', element).val('SENTENCE');
        $('.cardstories_write_sentence .cardstories_submit', element).submit();
    };

    $.cardstories.
        create(player_id, $('#qunit-fixture .cardstories')).
        done(function() {
            var first_card = $('.cardstories_cards_hand .cardstories_card:nth(0)', element);
            first_card.click();
            $('.cardstories_card_confirm_ok', element).find('a').click();
        });
});

test("widget lobby", 4, function() {
    var player_id = 15;

    ok(!$('#qunit-fixture .cardstories').hasClass('cardstories_root'), 'no cardstories_root');
    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=state&type=lobby&modified=0&player_id=' + player_id + '&in_progress=true&my=true');
    };
    $('#qunit-fixture .cardstories').cardstories(player_id);
    ok($('#qunit-fixture .cardstories').hasClass('cardstories_root'), 'cardstories_root');
});

test("game", 5, function() {
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

test("game on error", 1, function() {
    $.cardstories.ajax = function(options) {
        var data = {error: 'error on game'};
        options.success(data);
    };

    $.cardstories.error = function(err) {
        equal(err, 'error on game', 'calls $.cardstories.error');
    };

    $.cardstories.game(11, 111, 'the root');
});

test("invitation_owner_modal_helper", 4, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_invitation .cardstories_owner', root);
    var modal = $('.cardstories_info', element);
    var overlay = $('.cardstories_modal_overlay', element);

    equal(modal.css('display'), 'none', 'Modal starts hidden');
    $.cardstories.invitation_owner_modal_helper(modal, overlay, function() {
        equal(modal.css('display'), 'block', 'Modal is shown on first run');
        modal.find('a').click();
        equal(modal.css('display'), 'none', 'Modal is closed');
        $.cardstories.invitation_owner_modal_helper(modal, overlay, function() {
            equal(modal.css('display'), 'none', 'Modal continues closed on second run.');
        });
    });
});

test("invitation_owner_slots_helper", 15, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_invitation .cardstories_owner', root);
    var slots = $('.cardstories_invite_friend', element);
    var player_id = 10;
    var game_id = 1;

    slots.each(function(i) {
        var slot = $(this);
        equal(slot.css('display'), 'none', 'slot ' + i + ' starts hidden');
    });

    $.cardstories.invitation_owner_slots_helper(slots, player_id, game_id, element, root, function() {
        slots.each(function(i) {
            var slot = $(this);
            equal(slot.css('display'), 'block', 'slot ' + i + ' is visible');
        });
        $.cardstories.invitation_owner_slots_helper(slots, player_id, game_id, element, root, function() {
            slots.each(function(i) {
                var slot = $(this);
                equal(slot.find('a').length, 1, 'slot ' + i + ' only has one anchor');
            });
        });
    });
});

asyncTest("invitation_owner_join_helper", 39, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_invitation .cardstories_owner', root);
    var player1 = 'player1';
    var player2 = 'player2';
    var player3 = 'player3';
    var player4 = 'player4';
    var state1 = {
        'owner_id': player1,
        'ready': false,
        'players': [ [ player1, null, 'n', null, [] ],
                     [ player2, null, 'n', null, [] ],
                     [ player3, null, 'n', 3, [] ] ]
    };

    var state2 = {
        'owner_id': player1,
        'ready': true,
        'players': [ [ player1, null, 'n', null, [] ],
                     [ player2, null, 'n', 2, [] ],
                     [ player3, null, 'n', 3, [] ],
                     [ player4, null, 'n', null, [] ] ]
    };

    for (var i=1; i<=5; i++) {
        equal($('#cardstories_player_join_' + i, root).css('display'), 'none', 'movie ' + i + ' starts hidden');
    }

    // Count how often animate_sprite is called.
    $.cardstories.animate_sprite = function(movie, fps, frames, cb) {
        ok(true, 'counting animate_sprite');
        movie.show();
        cb();
    }

    $.cardstories.display_modal($('.cardstories_info', element), $('.cardstories_modal_overlay', element));
    $.cardstories.invitation_owner_join_helper(player1, state1, element, root, function() {
        equal($('.cardstories_modal_overlay', element).css('display'), 'none', 'modal overlay is hidden');
        equal($('.cardstories_go_vote', element).css('display'), 'block', 'go_vote is shown');
        ok($('.cardstories_go_vote .cardstories_modal_button', element).hasClass('cardstories_button_disabled'), 'go_vote button is disabled');
        equal($('.cardstories_player_arms_1', element).css('display'), 'block', 'arm 1 is visible');
        equal($('.cardstories_player_arms_2', element).css('display'), 'block', 'arm 2 is visible');
        equal($('.cardstories_player_arms_3', element).css('display'), 'none', 'arm 3 is hidden');
        equal($('.cardstories_player_arms_4', element).css('display'), 'none', 'arm 4 is hidden');
        equal($('.cardstories_player_arms_5', element).css('display'), 'none', 'arm 5 is hidden');
        equal($('.cardstories_active_friend.cardstories_friend_slot1', element).css('display'), 'block', 'Active slot 1 is visible');
        equal($('.cardstories_active_friend.cardstories_friend_slot2', element).css('display'), 'block', 'Active slot 2 is visible');
        equal($('.cardstories_active_friend.cardstories_friend_slot3', element).css('display'), 'none', 'Active slot 3 is hidden');
        equal($('.cardstories_active_friend.cardstories_friend_slot4', element).css('display'), 'none', 'Active slot 4 is hidden');
        equal($('.cardstories_active_friend.cardstories_friend_slot5', element).css('display'), 'none', 'Active slot 5 is hidden');
        ok($('.cardstories_active_friend.cardstories_friend_slot1', element).hasClass('cardstories_active_friend_picking'), 'Active slot 1 is picking');
        ok($('.cardstories_active_friend.cardstories_friend_slot2', element).hasClass('cardstories_active_friend_picked'), 'Active slot 2 picked');

        // Call it again: animate_sprite should only be called again when
        // necessary and the number of expected assertions should reflect this.
        $.cardstories.invitation_owner_join_helper(player1, state2, element, root, function() {
            ok(!$('.cardstories_go_vote .cardstories_modal_button', element).hasClass('cardstories_button_disabled'), 'go_vote button is enabled');
            equal($('.cardstories_player_arms_1', element).css('display'), 'block', 'arm 1 is visible');
            equal($('.cardstories_player_arms_2', element).css('display'), 'block', 'arm 2 is visible');
            equal($('.cardstories_player_arms_3', element).css('display'), 'block', 'arm 3 is visible');
            equal($('.cardstories_player_arms_4', element).css('display'), 'none', 'arm 4 is hidden');
            equal($('.cardstories_player_arms_5', element).css('display'), 'none', 'arm 5 is hidden');
            equal($('.cardstories_active_friend.cardstories_friend_slot1', element).css('display'), 'block', 'Active slot 1 is visible');
            equal($('.cardstories_active_friend.cardstories_friend_slot2', element).css('display'), 'block', 'Active slot 2 is visible');
            equal($('.cardstories_active_friend.cardstories_friend_slot3', element).css('display'), 'block', 'Active slot 3 is visible');
            equal($('.cardstories_active_friend.cardstories_friend_slot4', element).css('display'), 'none', 'Active slot 4 is hidden');
            equal($('.cardstories_active_friend.cardstories_friend_slot5', element).css('display'), 'none', 'Active slot 5 is hidden');
            ok($('.cardstories_active_friend.cardstories_friend_slot1', element).hasClass('cardstories_active_friend_picked'), 'Active slot 1 picked');
            ok($('.cardstories_active_friend.cardstories_friend_slot2', element).hasClass('cardstories_active_friend_picked'), 'Active slot 2 picked');
            ok($('.cardstories_active_friend.cardstories_friend_slot3', element).hasClass('cardstories_active_friend_picking'), 'Active slot 3 is picking');
            start();
        });
    });
});

asyncTest("invitation_owner_go_vote_confirm", 28, function() {
    var root = $('#qunit-fixture .cardstories');
    var container = $('.cardstories_invitation', root);
    var element = $('.cardstories_owner', container);
    var player1 = 'player1';
    var player2 = 'player2';
    var player3 = 'player3';
    var player4 = 'player4';

    var state = {
        owner_id: player1,
        winner_card: 7,
        ready: true,
        players: [[player1, null, 'n', null, []],
                  [player2, null, 'n', 4, []],
                  [player3, null, 'n', 6, []],
                  [player4, null, 'n', null, []]]
    };

    $.cardstories.ajax = function(options) {
        start();
    };

    // Simulate set_active().
    container.show();
    element.show();

    var go_vote_box = $('.cardstories_go_vote', element);
    var go_vote_button = go_vote_box.find('a');
    var confirmation_box = $('.cardstories_go_vote_confirm', element);
    var ok_button = $('.cardstories_go_vote_confirm_yes', confirmation_box);
    var cancel_button = $('.cardstories_go_vote_confirm_no', confirmation_box);
    var pick_1 = $('#cardstories_player_pick_1', element);
    var pick_2 = $('#cardstories_player_pick_2', element);
    var pick_3 = $('#cardstories_player_pick_3', element);
    var card_1 = pick_1.find('.cardstories_card');
    var card_2 = pick_2.find('.cardstories_card');
    var card_3 = pick_3.find('.cardstories_card');
    var final_left_1 = card_1.metadata({type: 'attr', name: 'data'}).final_left;
    var final_left_2 = card_2.metadata({type: 'attr', name: 'data'}).final_left;
    var final_left_3 = card_3.metadata({type: 'attr', name: 'data'}).final_left;

    // Count how often animate_sprite is called.
    $.cardstories.animate_sprite = function(movie, fps, frames, cb) {
        ok(true, 'counting animate_sprite');
        movie.show();
        cb();
    }

    equal(pick_1.css('display'), 'none', 'card 1 is not visible before animation');
    equal(pick_2.css('display'), 'none', 'card 2 is not visible before animation');
    equal(pick_3.css('display'), 'none', 'card 3 is not visible before animation');

    $.cardstories.invitation_owner(player1, state, root, function() {
        go_vote_button.click();
        equal(confirmation_box.css('display'), 'block', 'confirmation box is visible');
        equal(go_vote_box.css('display'), 'none', 'go to vote box is not visible');

        cancel_button.click();
        equal(confirmation_box.css('display'), 'none', 'confirmation box is not visible after canceling');
        equal(go_vote_box.css('display'), 'block', 'go to vote box is visible again after canceling');

        ok(!pick_1.hasClass('cardstories_no_background'), 'pick 1 sprite is visible');
        ok(!pick_2.hasClass('cardstories_no_background'), 'pick 2 sprite is visible');
        ok(!pick_3.hasClass('cardstories_no_background'), 'pick 3 sprite is visible');

        notEqual(card_1.css('display'), 'none', 'card 1 is visible after animation');
        notEqual(card_2.css('display'), 'none', 'card 2 is visible after animation');
        equal(card_3.css('display'), 'none', 'card 3 is not visible after animation because the player didn not pick a card');

        notEqual(card_1.position().left, final_left_1, 'card 1 is further from the slot than its final position');
        notEqual(card_2.position().left, final_left_2, 'card 2 is further from the slot than its final position');

        go_vote_button.click();
        ok_button.click();
        equal(confirmation_box.css('display'), 'none', 'confirmation box is not visible after confirmation');
        ok(pick_1.hasClass('cardstories_no_background'), 'pick 1 sprite is hidden');
        ok(pick_2.hasClass('cardstories_no_background'), 'pick 2 sprite is hidden');
        equal(card_1.position().left, final_left_1, 'card 1 is at its final position');
        equal(card_2.position().left, final_left_2, 'card 2 is at its final position');
    });
});

test("invitation_owner_invite_more", 4, function() {
    var player1 = 'player1';
    var card1 = 5;
    var player2 = 'player2';
    var player_id = player1;
    var game_id = 101;

    var game = {
        'id': game_id,
        'owner': true,
        'ready': true,
        'winner_card': 10,
        'players': [ [ player1, null, 'n', card1, [] ],
                     [ player2, null, 'n', null, [] ] ],
        'invited': [ player2 ]
    };

    var element = $('#qunit-fixture .cardstories_invitation .cardstories_owner');
    var advertise = $('.cardstories_advertise', element);
    var textarea = $('.cardstories_advertise_input textarea', advertise);

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) { };
    $.cardstories.ajax = function(options) { };

    ok(!element.hasClass('cardstories_active'));
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    ok(element.hasClass('cardstories_active'));
    $.cookie('CARDSTORIES_INVITATIONS', 'UNEXPECTED');
    $('.cardstories_invite_friend', element).first().click();
    equal(advertise.css('display'), 'block');
    equal(textarea.val(), textarea.attr('placeholder'));
});

asyncTest("invitation_owner", 7, function() {
    var player1 = 'player1';
    var player2 = 'player2';
    var player3 = 'player3';
    var player4 = 'player4';
    var card1 = 5;
    var player_id = player1;
    var game_id = 101;
    var winner_card = 7;
    var sentence = 'SENTENCE';

    var game = {
        'id': game_id,
        'owner': true,
        'ready': true,
        'sentence': sentence,
        'winner_card': winner_card,
        'players': [ [ player1, null, 'n', card1, [] ],
                     [ player2, null, 'n', null, [] ],
                     [ player3, null, 'n', 9, [] ],
                     [ player4, null, 'n', 16, [] ] ],
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
    $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner .cardstories_sentence').text(), sentence);

    var picked_card = $('#qunit-fixture .cardstories_invitation .cardstories_owner .cardstories_picked_card');
    var winner_src = picked_card.metadata({type: 'attr', name: 'data'}).card.supplant({card: winner_card});
    equal(picked_card.find('.cardstories_card_foreground').attr('src'), winner_src, 'the picked card is shown');

    // TODO: Test card display when new display logic is implemented.
    /*
    var cards = $('#qunit-fixture .cardstories_invitation .cardstories_owner .cardstories_cards');
    equal($('.cardstories_card:nth(0) .cardstories_card_foreground', cards).attr('alt'), player1);
    equal($('.cardstories_card:nth(0) .cardstories_card_foreground', cards).attr('src'), 'PATH/card0' + card1 + '.png');
    equal($('.cardstories_card:nth(1) .cardstories_card_foreground', cards).attr('alt'), player2);
    equal($('.cardstories_card:nth(1) .cardstories_card_foreground', cards).attr('src'), 'PATH/card-back.png');
    equal($('.cardstories_card:nth(2) .cardstories_card_foreground', cards).attr('alt'), 'Waiting');
    equal($('.cardstories_card:nth(2) .cardstories_card_foreground', cards).attr('src'), 'PATH/card-back.png');
    equal($('#qunit-fixture .cardstories_invitation .cardstories_owner.cardstories_active').length, 1);
    */
    $('#qunit-fixture .cardstories_owner .cardstories_go_vote .cardstories_modal_button').click();
    $('#qunit-fixture .cardstories_owner .cardstories_go_vote_confirm_yes').click();
});

asyncTest("invitation_pick", 11, function() {
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
            $('#qunit-fixture .cardstories_invitation .cardstories_card_confirm_ok').find('a').click();
            start();
        };

        game.self[0] = picked;
        $.cardstories.invitation(player_id, game, $('#qunit-fixture .cardstories'));
    };

    $.cardstories.
        invitation(player_id, game, $('#qunit-fixture .cardstories')).
        done(function(is_ready) {
            var card_template = $('#qunit-fixture .cardstories_invitation .cardstories_pick .cardstories_card_template');
            var meta = card_template.metadata({type: 'attr', name: 'data'});
            equal($('#qunit-fixture .cardstories_invitation .cardstories_pick.cardstories_active').length, 1);
            equal($('#qunit-fixture .cardstories_invitation .cardstories_pick .cardstories_sentence').text(), sentence); // invitation_board function side effect
            equal($('.cardstories_card:nth(0) .cardstories_card_foreground', element).attr('src'), meta.card.supplant({card: cards[0]}));//'PATH/card0' + cards[0] + '.png');
            equal($('.cardstories_card:nth(5) .cardstories_card_foreground', element).attr('src'), meta.card.supplant({card: cards[5]}));//'PATH/card0' + cards[5] + '.png');
            $('.cardstories_card:nth(4)', element).click();
            $('#qunit-fixture .cardstories_invitation .cardstories_card_confirm_ok').find('a').click();

            window.setTimeout(invitation_picked, 50);
        });

});

test("invitation_pick_wait", 8, function() {
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

test("invitation_anonymous", 2, function() {
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

test("invitation_board", 27, function() {
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
    equal($('.cardstories_sentence', element).first().text(), sentence);
    // anonymous view, all players present
    equal($('.cardstories_owner_seat .cardstories_player_name', element).text(), owner);
    for(var i = 1; i <= 5; i++) {
        equal($('.cardstories_player_seat_' + i + ' .cardstories_player_name', element).text(), 'player' + i);
    }
    // player view, all players present
    player_id = player1;
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

test("invitation_board_seat", 3, function() {
    var player_id = 100;
    var card1 = 10;
    var card2 = 20;
    var card3 = 30;
    var game = {};

    var element = $('#qunit-fixture .cardstories_invitation .cardstories_board .cardstories_owner_seat');
    var player = [ 'player1', card1, 'y', card3, [card1, card2] ];
    $.cardstories.invitation_board_seat(player_id, game, $('#qunit-fixture .cardstories'), element, player, 'owner');
    ok(element.hasClass('cardstories_player_picked'), 'picked');
    ok(element.hasClass('cardstories_player_voted'), 'voted');
    ok(element.hasClass('cardstories_player_won'), 'won');
});

test("invitation_participate", 11, function() {
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

test("widget invitation", 7, function() {
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

asyncTest("vote_voter", 18, function() {
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
            $('#qunit-fixture .cardstories_vote .cardstories_card_confirm_ok').find('a').click();
            start();
        };

        game.self[1] = voted;
        $.cardstories.vote(player_id, game, $('#qunit-fixture .cardstories'));
    };

    $.cardstories.
        vote(player_id, game, $('#qunit-fixture .cardstories')).
        done(function(is_ready) {
            var card_template = $('.cardstories_card_template', element);
            var meta = card_template.metadata({type: 'attr', name: 'data'});
            equal($('#qunit-fixture .cardstories_vote .cardstories_voter.cardstories_active').length, 1);
            equal($('#qunit-fixture .cardstories_voter .cardstories_sentence').text(), sentence);
            for(var i = 0; i < board.length; i++) {
                equal($('.cardstories_card:nth(' + i + ') .cardstories_card_foreground', element).attr('src'), meta.card.supplant({card: board[i]}));
            }
            equal($('.cardstories_card:nth(0) .cardstories_card_foreground', element).attr('alt'), ' ', 'card0 alt was reset');
            equal($('.cardstories_card:nth(1) .cardstories_card_foreground', element).attr('alt'), ' My Card', 'card1 alt was set');
            equal($('.cardstories_card:nth(5) .cardstories_card_foreground', element).attr('src'), meta.nocard);
            $('.cardstories_picked', element).click(); // must do nothing
            $('.cardstories_card:nth(4)', element).click();
            $('#qunit-fixture .cardstories_vote .cardstories_card_confirm_ok').find('a').click();

            window.setTimeout(vote_voted, 50);
        });
});

test("invitation_voter_wait", 8, function() {
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

test("vote_anonymous", 3, function() {
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

test("vote_viewer", 7, function() {
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

test("vote_owner_morph_master_card", 4, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_vote .cardstories_owner', root);
    var card = $('.cardstories_card_6', element);
    var template = $('.cardstories_card_template', element);

    notEqual(template.css('display'), 'none', 'Template is visible');
    equal(card.css('display'), 'none', 'Card is invisible');
    $.cardstories.vote_owner_morph_master_card(element, function () {
        equal(template.css('display'), 'none', 'Template is invisible');
        notEqual(card.css('display'), 'none', 'Card is visible');
    });
});

test("vote_owner_shuffle_cards", 7, function() {
    var root = $('#qunit-fixture .cardstories');
    var container = $('.cardstories_vote', root);
    var element = $('.cardstories_owner', container);
    var game = {
        'owner_id': 'Owner',
        'players': [ [ 'Owner', null, null, 1, [] ],
                     [ 'Player 1', null, null, null, [] ],
                     [ 'Player 2', null, null, 2, [] ],
                     [ 'Player 3', null, null, 3, [] ] ]
    };

    // Simulate set_active().
    container.show();
    element.show();

    var card1_l = $('.cardstories_card_1', element).show().position().left;
    var card2_l = $('.cardstories_card_2', element).show().position().left;
    var card3_l = $('.cardstories_card_3', element).show().position().left;
    var card4_l = $('.cardstories_card_4', element).show().position().left;
    var card5_l = $('.cardstories_card_5', element).show().position().left;
    var card6_l = $('.cardstories_card_6', element).show().position().left;
    $.cardstories.vote_owner_shuffle_cards(game, element, function() {
        // Check that the sentence box was moved into position.
        var sentence = $('.cardstories_sentence_box', element);
        var sentence_final_left = sentence.metadata({type: "attr", name: "data"}).fl;
        equal(sentence.position().left, sentence_final_left, 'sentence box was moved');

        // Check that cards were moved to the final positions.  The owner's
        // card is always number 6.
        equal($('.cardstories_card_1', element).show().position().left, card1_l, 'card 1 was not moved');
        notEqual($('.cardstories_card_2', element).show().position().left, card2_l, 'card 2 was moved');
        notEqual($('.cardstories_card_3', element).show().position().left, card3_l, 'card 3 was moved');
        equal($('.cardstories_card_4', element).show().position().left, card4_l, 'card 4 was not moved');
        equal($('.cardstories_card_5', element).show().position().left, card5_l, 'card 5 was not moved');
        notEqual($('.cardstories_card_6', element).show().position().left, card6_l, 'card 6 was moved');
    });
});

test("vote_owner_display_board", 14, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_vote .cardstories_owner', root);
    var owner_id = 'Owner';
    var player1 = 'Player 1';
    var player2 = 'Player 2';
    var player3 = 'Player 3';
    var game = {
        'owner_id': owner_id,
        'board': [],
        'players': [ [ owner_id, null, null, null, [] ],
                     [ player1, null, null, null, [] ],
                     [ player2, null, null, 2, [] ],
                     [ player3, 4, null, 3, [] ] ]
    };

    $.cardstories.vote_owner_display_board(game, element, root);

    notEqual($('.cardstories_friend_slot1', element).css('display'), 'none', 'first slot is visible');
    notEqual($('.cardstories_friend_slot2', element).css('display'), 'none', 'second slot is visible');
    notEqual($('.cardstories_friend_slot3', element).css('display'), 'none', 'third slot is visible');
    equal($('.cardstories_friend_slot1 .cardstories_active_friend_name', element).html(), player1, 'player 1 name is set');
    equal($('.cardstories_friend_slot2 .cardstories_active_friend_name', element).html(), player2, 'player 2 name is set');
    equal($('.cardstories_friend_slot3 .cardstories_active_friend_name', element).html(), player3, 'player 3 name is set');
    equal($('.cardstories_friend_slot4', element).css('display'), 'none', 'fourth slot is hidden');
    equal($('.cardstories_friend_slot5', element).css('display'), 'none', 'fifth slot is hidden');
    ok(!$('.cardstories_friend_slot1', element).hasClass('cardstories_active_friend_picking'), 'first slot is NOT voting');
    ok($('.cardstories_friend_slot2', element).hasClass('cardstories_active_friend_picking'), 'second slot is voting');
    ok($('.cardstories_friend_slot3', element).hasClass('cardstories_active_friend_voted'), 'third slot has voted');
    equal($('.cardstories_card_1', element).css('display'), 'none', 'card 1 is hidden');
    notEqual($('.cardstories_card_2', element).css('display'), 'none', 'card 2 is visible');
    notEqual($('.cardstories_card_3', element).css('display'), 'none', 'card 3 is visible');
});

test("vote_owner_display_cards", 8, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_vote .cardstories_owner', root);
    var owner_id = 'Owner';
    var player1 = 'Player 1';
    var player2 = 'Player 2';
    var player3 = 'Player 3';
    var board = [33,30,31,32];
    var game = {
        'owner_id': owner_id,
        'board': board,
        'winner_card': 30,
        'players': [ [ owner_id, null, null, 30, [] ],
                     [ player1, null, null, 31, [] ],
                     [ player2, null, null, 32, [] ],
                     [ player3, null, null, 33, [] ] ]
    };

    $.cardstories.vote_owner_display_cards(game, element, root, function() {
        for (var i=0; i < board.length; i++) {
            var slot = $('.cardstories_card_slot_' + (i + 1), element);
            notEqual(slot.css('display'), 'none', 'slot ' + i + ' is visible');
            equal(slot.find('.cardstories_card_foreground').attr('src'), '../css/images/card0' + board[i] + '.png', 'slot ' + i + ' shows card ' + board[i]);
        }
    });
});

asyncTest("vote_owner", 16, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_vote .cardstories_owner', root);
    var owner_id = 'Owner';
    var player1 = 'Player 1';
    var player2 = 'Player 2';
    var sentence = 'SENTENCE';
    var board = [32,30,31];
    var game_id = 100;
    var game = {
        'id': game_id,
        'owner': true,
        'owner_id': owner_id,
        'sentence': sentence,
        'ready': true,
        'board': board,
        'winner_card': 30,
        'players': [ [ owner_id, null, null, 30, [] ],
                     [ player1, 30, null, 31, [] ],
                     [ player2, 30, null, 32, [] ] ]
    };

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=complete&owner_id=' + owner_id + '&game_id=' + game_id);
        var destel = $('.cardstories_complete', root);
        equal($('.cardstories_card_slot_1', element).css('top'), $('.cardstories_card_slot_2', destel).css('top'), 'card 1 in slot 2');
        equal($('.cardstories_card_slot_1', element).css('left'), $('.cardstories_card_slot_2', destel).css('left'), 'card 1 in slot 2');
        equal($('.cardstories_card_slot_2', element).css('top'), $('.cardstories_picked_card', destel).css('top'), 'card 2 in author spot');
        equal($('.cardstories_card_slot_2', element).css('left'), $('.cardstories_picked_card', destel).css('left'), 'card 2 in author spot');
        equal($('.cardstories_card_slot_3', element).css('top'), $('.cardstories_card_slot_1', destel).css('top'), 'card 3 in slot 1');
        equal($('.cardstories_card_slot_3', element).css('left'), $('.cardstories_card_slot_1', destel).css('left'), 'card 3 in slot 1');
        equal($('.cardstories_sentence_box', element).css('top'), $('.cardstories_sentence_box', destel).css('top'), 'sentence box was moved');
        equal($('.cardstories_sentence_box', element).css('left'), $('.cardstories_sentence_box', destel).css('left'), 'sentence box was moved');
        start();
    };

    $.cardstories.poll_ignore = function(ignored_request, ignored_answer, new_poll, old_poll) {
      equal(ignored_request.game_id, game_id, 'poll_ignore request game_id');
      equal(new_poll, undefined, 'poll_ignore metadata not set');
    };

    ok(!element.hasClass('cardstories_active'), 'element is inactive');
    $.cardstories.vote(owner_id, game, root);
    ok(element.hasClass('cardstories_active'), 'element is active');
    equal($('.cardstories_sentence', element).text(), sentence, 'sentence is set');
    var button = $('.cardstories_results_announce .cardstories_modal_button', element);
    ok(!button.hasClass('cardstories_button_disabled'), 'announce button is enabled');
    button.click();
    $('.cardstories_results_confirm_yes', element).click();
});

test("complete owner lost easy", 7, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_complete', root);
    var owner_id = 'Owner';
    var player1 = 'Player 1';
    var player2 = 'Player 2';
    var game = {
        'owner': true,
        'owner_id': owner_id,
        'board': [],
        'winner_card': 30,
        'players': [ [ owner_id, null, 'n', 30, [] ],
                     [ player1, 30, 'y', 31, [] ],
                     [ player2, 30, 'y', 32, [] ] ]
    };

    $.cardstories.complete(owner_id, game, root);
    var box = $('.cardstories_results', element);
    notEqual(box.css('display'), 'none', 'box is visible');
    notEqual(box.find('p.cardstories_lost_1').css('display'), 'none', 'lost 1 text is visible');
    equal(box.find('p.cardstories_lost_2').css('display'), 'none', 'lost 2 text is hidden');
    equal(box.find('p.cardstories_won').css('display'), 'none', 'won text is hidden');
    notEqual(box.find('img.cardstories_lost_1').css('display'), 'none', 'lost 1 img is visible');
    equal(box.find('img.cardstories_lost_2').css('display'), 'none', 'lost 2 img is hidden');
    equal(box.find('img.cardstories_won').css('display'), 'none', 'won img is hidden');
});

test("complete owner lost hard", 7, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_complete', root);
    var owner_id = 'Owner';
    var player1 = 'Player 1';
    var player2 = 'Player 2';
    var game = {
        'owner': true,
        'owner_id': owner_id,
        'board': [],
        'winner_card': 30,
        'players': [ [ owner_id, null, 'n', 30, [] ],
                     [ player1, 32, 'y', 31, [] ],
                     [ player2, 31, 'y', 32, [] ] ]
    };

    $.cardstories.complete(owner_id, game, root);
    var box = $('.cardstories_results', element);
    notEqual(box.css('display'), 'none', 'box is visible');
    equal(box.find('p.cardstories_lost_1').css('display'), 'none', 'lost 1 text is hidden');
    notEqual(box.find('p.cardstories_lost_2').css('display'), 'none', 'lost 2 text is visible');
    equal(box.find('p.cardstories_won').css('display'), 'none', 'won text is hidden');
    equal(box.find('img.cardstories_lost_1').css('display'), 'none', 'lost 1 img is hidden');
    notEqual(box.find('img.cardstories_lost_2').css('display'), 'none', 'lost 2 img is visible');
    equal(box.find('img.cardstories_won').css('display'), 'none', 'won img is hidden');
});

test("complete owner won", 7, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_complete', root);
    var owner_id = 'Owner';
    var player1 = 'Player 1';
    var player2 = 'Player 2';
    var game = {
        'owner': true,
        'owner_id': owner_id,
        'board': [],
        'winner_card': 30,
        'players': [ [ owner_id, null, 'y', 30, [] ],
                     [ player1, 30, 'y', 31, [] ],
                     [ player2, 31, 'n', 32, [] ] ]
    };

    $.cardstories.complete(owner_id, game, root);
    var box = $('.cardstories_results', element);
    notEqual(box.css('display'), 'none', 'box is visible');
    equal(box.find('p.cardstories_lost_1').css('display'), 'none', 'lost 1 text is hidden');
    equal(box.find('p.cardstories_lost_2').css('display'), 'none', 'lost 2 text is hidden');
    notEqual(box.find('p.cardstories_won').css('display'), 'none', 'won text is visible');
    equal(box.find('img.cardstories_lost_1').css('display'), 'none', 'lost 1 img is hidden');
    equal(box.find('img.cardstories_lost_2').css('display'), 'none', 'lost 2 img is hidden');
    notEqual(box.find('img.cardstories_won').css('display'), 'none', 'won img is visible');
});

test("complete", 26, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_complete', root);
    var owner_id = 'Owner';
    var player1 = 'Player 1';
    var player2 = 'Player 2';
    var player3 = 'Player 3';
    var player4 = 'Player 4';
    var game = {
        'owner': true,
        'owner_id': owner_id,
        'board': [],
        'winner_card': 30,
        'players': [ [ owner_id, null, 'y', 30, [] ],
                     [ player1, 30, 'y', 31, [] ],
                     [ player2, 31, 'n', 32, [] ],
                     [ player3, 32, 'n', 33, [] ],
                     [ player4, 30, 'y', 34, [] ] ]
    };

    equal($('#qunit-fixture .cardstories_complete.cardstories_active').length, 0);
    $.cardstories.complete(owner_id, game, root);
    equal($('#qunit-fixture .cardstories_complete.cardstories_active').length, 1);

    notEqual($('.cardstories_friend_slot1', element).css('display'), 'none', 'first slot is visible');
    notEqual($('.cardstories_friend_slot2', element).css('display'), 'none', 'second slot is visible');
    notEqual($('.cardstories_friend_slot3', element).css('display'), 'none', 'third slot is visible');
    notEqual($('.cardstories_friend_slot4', element).css('display'), 'none', 'fourth slot is visible');
    equal($('.cardstories_friend_slot1 .cardstories_active_friend_name', element).html(), player1, 'player 1 name is set');
    equal($('.cardstories_friend_slot2 .cardstories_active_friend_name', element).html(), player2, 'player 2 name is set');
    equal($('.cardstories_friend_slot3 .cardstories_active_friend_name', element).html(), player3, 'player 3 name is set');
    equal($('.cardstories_friend_slot4 .cardstories_active_friend_name', element).html(), player4, 'player 4 name is set');
    equal($('.cardstories_friend_slot5', element).css('display'), 'none', 'fifth slot is hidden');
    notEqual($('.cardstories_card_slot_1', element).css('display'), 'none', 'card 1 is visible');
    notEqual($('.cardstories_card_slot_2', element).css('display'), 'none', 'card 2 is visible');
    notEqual($('.cardstories_card_slot_3', element).css('display'), 'none', 'card 3 is visible');
    notEqual($('.cardstories_card_slot_4', element).css('display'), 'none', 'card 4 is visible');
    equal($('.cardstories_card_slot_5', element).css('display'), 'none', 'card 5 is hidden');
    ok($('.cardstories_friend_slot1', element).hasClass('cardstories_active_friend_won'), 'friend 1 won');
    ok($('.cardstories_friend_slot2', element).hasClass('cardstories_active_friend_lost'), 'friend 2 lost');
    ok($('.cardstories_friend_slot3', element).hasClass('cardstories_active_friend_lost'), 'friend 3 lost');
    ok($('.cardstories_friend_slot4', element).hasClass('cardstories_active_friend_won'), 'friend 4 won');
    ok($('.cardstories_votes_1', element).children().length == 1, '1 vote for player 1');
    ok($('.cardstories_votes_2', element).children().length == 1, '1 vote for player 2');
    ok($('.cardstories_votes_3', element).children().length == 0, 'no votes for player 3');
    ok($('.cardstories_votes_4', element).children().length == 0, 'no votes for player 4');
    ok($('.cardstories_votes_5', element).children().length == 0, 'no votes for player 5');
    ok($('.cardstories_votes_win', element).children().length == 2, '2 winning votes');
});

test("play_again_finish_state", 4, function() {
    var player_id = 5;
    var game = {
        'id': 7,
        'owner': true,
        'state': 'fake_state',
        'board': [],
        'players': []
    };
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_invitation .cardstories_owner', root);
    var advertise = $('.cardstories_invitation .cardstories_owner .cardstories_advertise', element);
    $.cardstories.complete(player_id, game, root);
    notEqual($('.cardstories_play_again', root).css('display'), 'none', 'Play again button is visible when the player is owner');
    var create = $.cardstories.create;
    var send_game = $.cardstories.send_game;
    var $textarea = $('.cardstories_text', advertise);
    $.cookie('CARDSTORIES_INVITATIONS', null);
    $textarea.val('aaa@aaa.aaa\nbbb@bbb.bbb\nccc@ccc.ccc');
    var text = $textarea.val();
    $.cardstories.send_game = function () {}; //do nothing
    $.cardstories.advertise(player_id, game.id, element);
    $('.cardstories_submit', advertise).click();
    $.cardstories.send_game = send_game;
    var inv_cookie = $.cookie('CARDSTORIES_INVITATIONS');
    $.cardstories.create = function (arg_player_id, arg_root) {
        equal(arg_player_id, player_id);
        equal(arg_root, root);
        $.cardstories.create = create;
    };
    $('.cardstories_play_again', root).click();
    equal(text, inv_cookie);
});

test("advertise", 11, function() {
    var owner_id = 15;
    var game_id = 100;
    var element = $('#qunit-fixture .cardstories_invitation .cardstories_owner');
    var advertise = $('.cardstories_advertise', element);
    var textarea = $('.cardstories_advertise_input textarea', advertise);
    var submit_button = $('.cardstories_send_invitation', advertise);
    var feedback = $('.cardstories_advertise_feedback', advertise);

    $.cardstories.ajax = function(options) {
        equal(options.type, 'GET');
        equal(options.url, $.cardstories.url + '?action=invite&owner_id=' + owner_id + '&game_id=' + game_id + '&player_id=player1&player_id=player2');
    };

    // the list of invitations is filled by the user
    $.cookie('CARDSTORIES_INVITATIONS', null);
    var text = " \n \t player1 \n\n   \nplayer2";
    textarea.val(text);
    $.cardstories.advertise(owner_id, game_id, element);
    submit_button.click();
    equal($.cookie('CARDSTORIES_INVITATIONS'), text);
    equal(feedback.css('display'), 'block', 'Feedback text is visible after submitting');
    equal(textarea.css('display'), 'none', 'Textarea is not visible after submitting');
    equal(submit_button.css('display'), 'none', 'Submit button is not visible after submitting');

    // the list of invitations is retrieved from the cookie
    textarea.val('UNEXPECTED');
    $.cardstories.advertise(owner_id, game_id, element);
    equal(textarea.val(), text);

    $.cookie('CARDSTORIES_INVITATIONS', null);
    textarea.val('');
    $.cardstories.advertise(owner_id, game_id, element);

    // button should be enabled only when text is not blank
    text = 'player1';
    ok(submit_button.hasClass('cardstories_button_disabled'), 'button should be disabled');
    textarea.val(text).keyup();
    ok(!submit_button.hasClass('cardstories_button_disabled'), 'button should be enabled');

    // clicking on invite friend button again doesn't do any harm.
    $('.cardstories_invite_friend', element).first().click();
    equal(textarea.val(), text);

    $('.cardstories_advertise_close', advertise).click();
    equal(advertise.css('display'), 'none', 'clicking the close button hides the dialog');
});

test("refresh_lobby", 15, function() {
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

test("refresh_lobby on error", 1, function() {
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

test("lobby_games", 24, function() {
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

test("lobby_games without games", 1, function() {
    var player_id = 10;
    var games = {games: [], win: {}};
    var element = $('#qunit-fixture .cardstories .cardstories_games_test');
    $.cardstories.lobby_games(player_id, games, element, $('#qunit-fixture .cardstories'));
    equal($('.cardstories_pager', element).css('display'), 'none', 'pager is hidden');
});

asyncTest("create_pick_card_animate", 30, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_pick_card', root);
    var card_specs = [{value: 1}, {value: 2}, {value: 3}, {value: 4}, {value: 5}, {value: 6}];
    var cards = $('.cardstories_deck .cardstories_card', element);

    // Make sure the container (and its ancestors) are visible before measuring top and left,
    // otherwise some versions of FF report bad values.
    var container = $('.cardstories_cards', element).show();
    container.parents().show();
    var final_top = parseInt(container.css('top'), 10);

    var src_template = $('.cardstories_card_template', element).metadata({type: 'attr', name: 'data'}).card;

    cards.each(function() {
        var card = $(this);
        var meta = card.metadata({type: 'attr', name: 'data'});
        ok(parseInt(card.css('left'), 10) < meta.final_left, 'card starts more left than its final position');
        ok(parseInt(card.css('top'), 10) < final_top, 'card starts higher than its final position');
    });

    $.cardstories.create_pick_card_animate(card_specs, element, root, function() {
        cards.each(function(i) {
            var card = $(this);
            var meta = card.metadata({type: 'attr', name: 'data'});
            equal(parseInt(card.css('left'), 10), meta.final_left, 'card is animated to the left position defined by its metadata');
            equal(parseInt(card.css('top'), 10), final_top, 'card is animated to the final top position');
            equal(card.attr('src'), src_template.supplant({card: card_specs[cards.length - i - 1].value}), 'the foregournd image is shown');
        });
        start();
    });
});

asyncTest("create_pick_card_animate_fly_to_deck", 17, function() {
    var player_id = 42;
    var root = $('#qunit-fixture .cardstories');
    var container = $('.cardstories_create', root);
    var element = $('.cardstories_pick_card', container);
    container.show();
    element.show();
    var final_top = $('.cardstories_deck .cardstories_deck_cover', element).position().top;
    var final_left = $('.cardstories_deck .cardstories_deck_cover', element).position().left;
    var deck_cards = $('.cardstories_deck .cardstories_card', element);
    var board_cards = $('.cardstories_cards_hand .cardstories_card', element);

    $.cardstories.create_pick_card(player_id, root).done(function() {
        var card_index = 3;
        board_cards.eq(card_index + 1).addClass('cardstories_card_selected');

        $.cardstories.create_pick_card_animate_fly_to_deck(card_index, element, function() {
            board_cards.each(function(i) {
                var card = $(this);
                var display = card.hasClass('cardstories_card_selected') ? 'block' : 'none';
                equal(card.css('display'), display, 'only selected card is visible on the board');
            });

            deck_cards.each(function(i) {
                var card = $(this);
                if (i === card_index - 1) {
                    equal(card.css('display'), 'none', 'selected card is hidden');
                } else {
                    equal(card.position().top, final_top, 'card is animated back to the deck');
                    equal(card.position().left, final_left, 'card is animated back to the deck');
                }
            });

            start();
        });
    });
});

asyncTest("animate_center_picked_card", 3, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('#qunit-fixture .cardstories_create .cardstories_pick_card');
    var card_flyover = $('#qunit-fixture .cardstories_create .cardstories_pick_card .cardstories_card_flyover');
    var cards = [{'value':1},
                 {'value':2},
                 {'value':3},
                 {'value':4},
                 {'value':5},
                 {'value':6}];
    var selected = 1;

    root.addClass('cardstories_root');
    $('.cardstories_create .cardstories_pick_card .cardstories_cards', root).show();
    $.cardstories.set_active(root, $('.cardstories_create .cardstories_pick_card', root));

    // First display the dock
    var onReady = function(is_ready) {
        // Then select one of the cards
        $('.cardstories_cards_hand .cardstories_card', element).eq(selected).click();
    };
    var select = function(card, index, nudge, element) {
        equal(card_flyover.css('display'), 'none', 'flyover card is not visible initially');

        // And play the animation
        $.cardstories.animate_center_picked_card(element, index, card, function() {
            var meta = card_flyover.metadata({type: 'attr', name: 'data'});
            equal(card_flyover.css('display'), 'block', 'flyover card visible after animation');
            equal(card_flyover.position().left, meta.final_left, 'flyover card should be moved');

            // Remove selected attribute
            nudge();

            start();
        });
    };
    $.cardstories.
        display_or_select_cards('animate_center_picked_card',
                                cards,
                                select,
                                element,
                                root
                               ).
        done(onReady);
});

asyncTest("create_write_sentence_animate_start", 7, function() {
    var card = 12;
    var root = $('#qunit-fixture .cardstories');
    var element = root.find('.cardstories_create .cardstories_write_sentence');

    var write_box = $('.cardstories_write', element);
    var card_shadow = $('.cardstories_card_shadow', element);
    var card_template = $('.cardstories_card_template', element);
    var card_imgs = $('img', card_template);
    var card_foreground = card_imgs.filter('.cardstories_card_foreground');

    var final_width = card_imgs.width();
    var starting_width = 220;

    $.cardstories.create_write_sentence_animate_start(card, element, root, function(when) {
        if (when === 'before_animation') {
            equal(write_box.css('display'), 'none', 'write box is not visible initially');
            equal(card_shadow.css('display'), 'none', 'card shadow is not visible initially');
            ok(card_foreground.attr('src').match(card), 'src attribute is set properly to show the chosen card');
            equal(card_imgs.width(), starting_width, 'card starts out at starting width');
        } else if (when === 'after_animation') {
            equal(write_box.css('display'), 'block', 'write box is visible after animation');
            equal(card_shadow.css('display'), 'block', 'card shadow is visible after animation');
            equal(card_imgs.width(), final_width, 'after animation card grows to its original width');
            start();
        }
    });
});

asyncTest("create_write_sentence_animate_end", 14, function() {
    var card = 42;
    var root = $('#qunit-fixture .cardstories');
    var element = root.find('.cardstories_create .cardstories_write_sentence');

    var card_template = $('.cardstories_card_template', element);
    var card_img = $('img', card_template);
    var card_shadow = $('.cardstories_card_shadow', element);
    var final_element = $('.cardstories_invitation .cardstories_owner', root);
    var final_card_template = $('.cardstories_card_template', final_element);
    var write_box = $('.cardstories_write', element);
    var sentence_box = $('.cardstories_sentence_box', element);
    var final_sentence_box = $('.cardstories_sentence_box', final_element);

    var final_card_top = parseInt(final_card_template.css('top'), 10);
    var final_card_left = parseInt(final_card_template.css('left'), 10);
    var final_card_width = parseInt(final_card_template.css('width'), 10);
    var final_card_height = parseInt(final_card_template.css('height'), 10);
    var final_sentence_top = parseInt(final_sentence_box.css('top'), 10);
    var final_sentence_left = parseInt(final_sentence_box.css('left'), 10);
    var final_sentence_width = parseInt(final_sentence_box.css('width'), 10);
    var final_sentence_height = parseInt(final_sentence_box.css('height'), 10);

    equal(write_box.css('display'), 'block', 'write box is visible initially');
    equal(card_shadow.css('display'), 'block', 'card shadow is visible initially');
    equal(sentence_box.css('display'), 'none', 'sentence box is invisible initially');

    $.cardstories.create_write_sentence_animate_end(card, element, root, function() {
        equal(write_box.css('display'), 'none', 'write box is invisible after animation');
        equal(card_shadow.css('display'), 'none', 'card shadow is invisible after animation');
        equal(sentence_box.css('display'), 'block', 'sentence box is visible after animation');
        equal(card_img.width(), final_card_width);
        equal(card_img.height(), final_card_height);
        equal(parseInt(card_template.css('top'), 10), final_card_top);
        equal(parseInt(card_template.css('left'), 10), final_card_left);
        equal(sentence_box.width(), final_sentence_width);
        equal(sentence_box.height(), final_sentence_height);
        equal(parseInt(sentence_box.css('top'), 10), final_sentence_top);
        equal(parseInt(sentence_box.css('left'), 10), final_sentence_left);
        start();
    });
});

test("poll_discard", 3, function() {
    var root = $('#qunit-fixture .cardstories');
    $(root).metadata().poll = undefined;

    equal($.cardstories.poll_discard(root), undefined, 'noop on undefined');
    var poll = 1;
    $(root).metadata().poll = poll;
    equal($.cardstories.poll_discard(root), poll + 1, '++ to discard');
    equal($(root).metadata().poll, poll + 1, 'persists');
});

test("poll_ignore", function() {
    $.cardstories.poll_ignore = cardstories_default_poll_ignore;

    if (typeof console !== "undefined" && typeof console.log !== "undefined") {
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

test("start_story", 3, function() {
    var player_id = 222;
    var root = $('#qunit-fixture .cardstories');

    var poll = 1;
    $(root).metadata().poll = poll;

    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 0, 'pick_card not active');
    $.cardstories.start_story(player_id, root);
    equal($('#qunit-fixture .cardstories_create .cardstories_pick_card.cardstories_active').length, 1, 'pick_card active');
    equal($(root).metadata().poll, poll + 1);
});

test("lobby_in_progress", 10, function() {
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

test("lobby_finished", 10, function() {
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

test("poll", 18, function() {
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

asyncTest("display_or_select_cards move", 2, function() {
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
                                element,
                                root
                               ).
        done(onReady);
  });

asyncTest("display_or_select_cards select", 9, function() {
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
                                element,
                                root
                               ).
        done(onReady);
  });

asyncTest("display_or_select_cards select no bg", 4, function() {
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
    ok(background.attr('src'), 'src attribute is not blank');
    meta.card_bg = '';
    $.cardstories.
        display_or_select_cards('select no bg',
                                cards,
                                select,
                                element,
                                root
                               ).
        done(onReady);
  });

asyncTest("display_or_select_cards twice", 2, function() {
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
                                element,
                                root
                               ).
        done(function(is_ready) {
            check(is_ready);
            card1 = 22;
            $.cardstories.
                display_or_select_cards('twice',
                                        create_cards(card1),
                                        undefined,
                                        element,
                                        root
                                       ).
                done(function(is_ready) {
                    check(is_ready);
                    start();
                });
        });
  });

asyncTest("select_cards ok", 1, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create .cardstories_pick_card', root);
    $.cardstories.set_active(root, element);
    var confirm = $('.cardstories_card_confirm', element);
    var cards = [{'value':1},{'value':2},{'value':3},{'value':4},{'value':5},{'value':6}];
    var selected = 5;
    var onReady = function(is_ready) {
        $('.cardstories_cards_hand .cardstories_card', element).eq(selected).click();
        $('.cardstories_card_confirm_ok', element).find('a').click();
    };
    var ok_callback = function(card) {
        equal(cards[selected].value, card, 'selected card');
        start();
    };
    $.cardstories.
        select_cards('ok',
                     cards,
                     ok_callback,
                     element,
                     root).
        done(onReady);
  });

asyncTest("select_cards cancel", 1, function() {
    var root = $('#qunit-fixture .cardstories');
    var element = $('.cardstories_create', root);
    var confirm = $('.cardstories_card_confirm', element);
    var cards = [{'value':1},{'value':2},{'value':3},{'value':4},{'value':5},{'value':6}];
    var selected = 4;
    var onReady = function(is_ready) {
        $('.cardstories_cards_hand .cardstories_card', element).eq(selected).click();
        $('.cardstories_card_confirm_cancel', element).find('a').click();
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
                     element,
                     root).
        done(onReady);
  });

asyncTest("select_cards single", 6, function() {
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
                                element,
                                root
                               ).
        done(onReady);
  });

test("create_deck", 29, function() {
    var deck = $.cardstories.create_deck();
    var i;
    equal(deck.length, 7);
    while(deck.length > 0) {
        var card = deck.pop();
        equal(typeof card, "number");
        for(i = 0; i < deck.length; i++) {
            ok(deck[i] != card, 'duplicate of ' + card);
        }
    }
  });

test("credits", 4, function() {
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

asyncTest("solo", 4, function() {
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

test("solo on error", 1, function() {
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

test("poll on error", 1, function() {
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

test("trigger_keypress, trigger_keydown helpers", 4, function() {
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

test("onbeforeunload", 1, function() {
    $(window).trigger('beforeunload');
    equal($.cardstories.error, $.cardstories.noop, 'error handler gets set to a noop function on beforeunload');
});
