var selector = '#cardstories_chat_example';
var original_send = $.cardstories_chat.send;

function setup() {
    $(selector).cardstories_chat();
    $.cardstories_chat.send = original_send;
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

test("play_ring", 2, function() {
    var root = $(selector);
    $.cardstories_audio.play = function(sound_id, _root) {
        equal(sound_id, 'ring', 'calls $.cardstories_audio.play with "ring" sound id');
        equal(_root, root, 'calls $.cardstories_audio.play with the root element');
    };
    $.cardstories_chat.play_ring(root);
});
