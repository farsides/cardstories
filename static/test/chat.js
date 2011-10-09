var selector = '#cardstories_chat_example';
var original_send = $.cardstories_chat.send;

function setup() {
    $(selector).cardstories_chat();
    $.cardstories_chat.send = original_send;
    $.cardstories_audio = {play: $.noop};
}

module("cardstories_chat", {setup: setup});

test("state", 5, function() {
    var display = $(selector).find('.cardstories_chat_display');
    equal($.trim(display.html()), '', 'Display is initially empty');

    var messages = [
        {player_id: 16, sentence: 'Hello all!'},
        {player_id: 32, sentence: 'Goodbye all!'}
    ];
    $.cardstories_chat.state('Player', {messages: messages}, selector);

    ok(display.html().match('16'), 'Display shows player_id');
    ok(display.html().match('Hello all!'), 'Display shows sentence');
    ok(display.html().match('32'), 'Display shows player_id');
    ok(display.html().match('Goodbye all!'), 'Display shows sentence');
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
