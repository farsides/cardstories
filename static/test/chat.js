var selector = '#cardstories_chat_example';
var original_send = $.cardstories_chat.send;
var original_play_ring = $.cardstories_chat.play_ring;

function setup() {
    $(selector).cardstories_chat();
    $.cardstories_chat.send = original_send;
    $.cardstories_chat.play_ring = original_play_ring;
    $.cardstories_audio = {play: $.noop};
}

module("cardstories_chat", {setup: setup});

test("state", 8, function() {
    var display = $(selector).find('.cardstories_chat_display');
    equal($.trim(display.html()), '', 'Display is initially empty');

    var player1 = 'Player 1';
    var player2 = 'Player 2';
    var player3 = 'Player 3';
    var sentence1 = 'Hello all!';
    var sentence2 = 'Goodbye all!'
    var sentence3 = 'New game.'
    var game1 = 15;
    var messages = [
        {type: 'chat', player_id: player1, sentence: sentence1},
        {type: 'chat', player_id: player2, sentence: sentence2},
        {type: 'notification', game_id: game1, player_id: player3, sentence: sentence3}
    ];
    $.cardstories_chat.state('Player', {messages: messages}, selector);

    ok(display.html().match(player1), 'Display shows player_id');
    ok(display.html().match(sentence1), 'Display shows sentence');
    ok(display.html().match(player2), 'Display shows player_id');
    ok(display.html().match(sentence2), 'Display shows sentence');
    ok(display.html().match(player3), 'Display shows player_id');
    ok(display.html().match(sentence3), 'Display shows sentence');
    ok(display.html().match(game1), 'Display shows game URL');
});

test("pressing enter inside input field", 2, function() {
    $.cardstories_chat.send = function(player_id, line) {
        equal(line, 'I pressed enter!');
    };

    var input = $(selector).find('.cardstories_chat_input');
    var event = $.Event('keydown');
    event.which = 13; // Enter key

    // It shouldn't call plugin_send when input value is blank.
    input.val('  ');
    input.trigger(event);
    // It shouldn't call plugin_send when input value equals the placeholder.
    input.val(input.attr('placeholder'));
    input.trigger(event);
    // This, however, should work.
    input.val('I pressed enter!');
    input.trigger(event);
    equal(input.val(), '', 'The input value should be emptied after enter is pressed');
});

asyncTest("scroll", 1, function() {
    var root = $(selector);
    var display = $('.cardstories_chat_display', root);
    var data = {
        messages: [{
            type: 'notification',
            player_id: 'PLAYER_ID',
            game_id: 'GAME_ID',
            sentence: 'SENTENCE'
        }]
    };

    display.scroll(function() {
        ok(display.scrollTop() > 0);
        start();
    });

    for (var i = 0; i < 20; i++) {
        $.cardstories_chat.state('player_id', data, root);
    }
});

test("play_ring", 2, function() {
    var root = $(selector);
    $.cardstories_audio.play = function(sound_id, _root) {
        equal(sound_id, 'ring', 'calls $.cardstories_audio.play with "ring" sound id');
        equal(_root, root, 'calls $.cardstories_audio.play with the root element');
    };
    $.cardstories_chat.play_ring(root);
});

test("play ring sound on notification", 2, function() {
    var root = $(selector);
    var player_id = 'Player 1';
    var data = {
        messages: [{
            type: 'notification',
            player_id: 'PLAYER_ID',
            game_id: 'GAME_ID',
            sentence: 'SENTENCE'
        }]
    };
    var rang = 0;
    $.cardstories_chat.play_ring = function(_root) {
        rang++;
        equal(_root, root, 'calls $.cardstories_chat.play_ring with the root');
    };

    var root_data = root.data('cardstories_chat');
    // Set the timestamp to now so that play_ring won't be called.
    root_data.initialized_ts = new Date().getTime();
    root.data('cardstories_chat', root_data);
    $.cardstories_chat.state(player_id, data, root); // play_ring isn't called.
    // Now set the timestamp to over 5 seconds ago.
    root_data.initialized_ts = new Date().getTime() - 50001;
    root.data('cardstories_chat', root_data);
    $.cardstories_chat.state(player_id, data, root); // play_ring is called
    equal(rang, 1, 'play_ring should only be called once');
});
