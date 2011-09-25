module("cardstories_chat");

var selector = '#cardstories_chat_example';

var original_send = $.cardstories_chat.send;

function setup() {
    $(selector).cardstories_chat();
    $.cardstories_chat.send = original_send;
}

test("state", function() {
    setup();
    expect(5);

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

test("pressing enter inside input field", function() {
    setup();
    expect(2);

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
