var selector = '#cardstories_chat_example';
var original_send = $.cardstories_chat.send;
var original_play_sound = $.cardstories_chat.play_sound;
var cardstories_default_get_player_info_by_id = $.cardstories.get_player_info_by_id;

function setup() {
    $(selector).cardstories_chat();
    $.cardstories_chat.send = original_send;
    $.cardstories_chat.play_sound = original_play_sound;
    $.cardstories_audio = {play: $.noop};
    $.cardstories.get_player_info_by_id = function(player_id) { return {'name': "Player " + player_id } };
}

module("cardstories_chat", {setup: setup});

test("state", 8, function() {
    var display = $(selector).find('.cardstories_chat_display');
    equal($.trim(display.html()), '', 'Display is initially empty');

    var player1 = 1;
    var player2 = 2;
    var player3 = 3;
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

    ok(display.html().match('Player '+player1), 'Display shows player_id');
    ok(display.html().match(sentence1), 'Display shows sentence');
    ok(display.html().match('Player '+player2), 'Display shows player_id');
    ok(display.html().match(sentence2), 'Display shows sentence');
    ok(display.html().match('Player '+player3), 'Display shows player_id');
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

asyncTest("scroll", 3, function() {
    var root = $(selector);
    var display = $('.cardstories_chat_display', root);
    var messages = [];
    // Build up an array of 20 messages to scroll the chat window down.
    for (var i=0; i<20; i++) {
        messages.push({
            type: 'chat',
            player_id: 'PLAYER_ID',
            sentence: 'SENTENCE'
        });
    }

    equal(display.scrollTop(), 0, 'chat window is not scrolled down initially');

    // Chat window should scroll down after 'state' is called.
    display.one('scroll', function() {
        ok(display.scrollTop() > 0, 'window scrolls down after multiple messages are posted');

        // Manually scroll the chat window back up.
        display.scrollTop(0);

        // The chat window should scroll down even when 'state' is called
        // with an empty array (this happens in the game when going from the
        // lobby to the create state).
        display.one('scroll', function() {
            ok(display.scrollTop() > 0, 'window scrolls down after state function is called');
            start();
        });
        $.cardstories_chat.state('player_id', {messages: messages}, root);
    });
    $.cardstories_chat.state('player_id', {messages: messages}, root);
});

test("play_sound", 2, function() {
    var root = $(selector);
    var ts = new Date().getTime()-5001;
    $.cardstories_audio.play = function(sound_id, _root) {
        equal(sound_id, 'ring', 'calls $.cardstories_audio.play with "ring" sound id');
        equal(_root, root, 'calls $.cardstories_audio.play with the root element');
    };
    $.cardstories_chat.play_sound('ring', root, ts);

    // Set the timestamp to now so that play_ring won't be called.
    var ts = new Date().getTime();
    $.cardstories_audio.play = function(sound_id, _root) {
        ok(false, 'should not call $.cardstories_audio.play with recent timestamp');
    };
    $.cardstories_chat.play_sound('ring', root, ts);
});

test("play ring sound on notification", 3, function() {
    var root = $(selector);
    var player_id = 'Player 1';
    var data = {
        messages: [{
            type: 'notification',
            player_id: 'PLAYER_ID',
            sentence: 'SENTENCE'
        }]
    };
    var root_data = root.data('cardstories_chat');
    root_data.initialized_ts = new Date().getTime() - 50001;
    root.data('cardstories_chat', root_data);

    $.cardstories_chat.play_sound = function(sound_id, _root, ts) {
        equal(sound_id, 'ring', 'calls $.cardstories_chat.play_sound "ring"');
        equal(_root, root, 'calls $.cardstories_chat.play_sound with the root');
        equal(ts, root_data.initialized_ts, 'calls $.cardstories_chat.play_sound with the timestamp');
    };

    $.cardstories_chat.state(player_id, data, root); // play_ring is called
});

test("play pop sound on normal chat", 1, function() {
    var root = $(selector);
    var player_id = 'Player 1';
    var data = {
        messages: [{
            type: 'chat',
            player_id: 'PLAYER_ID',
            game_id: 'GAME_ID',
            sentence: 'SENTENCE'
        }]
    };
    var root_data = root.data('cardstories_chat');
    root_data.initialized_ts = new Date().getTime() - 50001;
    root.data('cardstories_chat', root_data);

    $.cardstories_chat.play_sound = function(sound_id, _root, ts) {
        equal(sound_id, 'pop', 'calls $.cardstories_chat.play_sound "pop"');
    };
    $.cardstories_chat.state(player_id, data, root); // play_ring is called
});


