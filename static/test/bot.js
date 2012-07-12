var selector = '#cardstories_bot_example';
var original_send = $.cardstories_bot.send;

function setup() {
    var root = $(selector);
    root.cardstories_bot();
    var player_id = 1011;
    var game_id = 149;
    $.cardstories_bot.load_game(player_id, game_id, {}, root);
    $.cardstories_bot.send = original_send;
}

module("cardstories_bot", {setup: setup});

test("state", 3, function() {
    var input = $(selector).find('#cardstories_bot_enable_join');
    ok(!input.is(':checked'), 'input starts unchecked');

    // Receive "enabled"
    $.cardstories_bot.state('player_id', {enable_join: true}, selector);
    ok(input.is(':checked'), 'input is checked');

    // Receive "disabled"
    $.cardstories_bot.state('player_id', {enable_join: false}, selector);
    ok(!input.is(':checked'), 'input is not checked');
});

test("clicking on checkbox", 1, function() {
    var input = $(selector).find('#cardstories_bot_enable_join');

    $.cardstories_bot.send = function(enable_join, player_id, game_id, root) {
        equal(enable_join, true);
    };

    input.click();
});
