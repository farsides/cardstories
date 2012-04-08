var selector = '#cardstories_root';
var default_cardstories_url_param = $.cardstories.url_param;
var default_cardstories_ajax = $.cardstories.ajax;
var default_cardstories_reload = $.cardstories.reload;
var default_cardstories_table_force_state_update = $.cardstories_table.force_state_update;

// Helper function to get keys from a JS object.
function get_keys(obj) {
    var keys = [];
    $.each(obj, function(key, val) { keys.push(key); });
    return keys;
}

function setup() {
    var root = $(selector);

    $.cardstories.url_param = function() { throw 'Please rebind "url_param"'; };
    $.cardstories.ajax = function() { throw 'Please rebind "ajax"'; };
    $.cardstories.reload = function() { throw 'Please rebind "reload"'; };

    $.cardstories_table.force_state_update = default_cardstories_table_force_state_update;
}

module("cardstories_table", {setup: setup});

test("init_create", 4, function() {
    var root = $(selector);
    var player_id = 1;

    $.cardstories.url_param = function(param_name) {
        if (param_name == 'create') { return 1; };
    };
    $.cardstories_table.force_state_update = function(_player_id, _game_id, _root) {
        ok(false, "Plugin shouldn't intervene when a game creation is explicitly requested");
    };

    root.cardstories_table(player_id, undefined);
    $.cardstories_table.load_game(player_id, undefined, {}, root);

    equal(get_keys($(root).data('cardstories_table').game2table).length, 1);
    equal($(root).data('cardstories_table').game2table[0].next_game_id, null);
    equal($(root).data('cardstories_table').game2table[0].next_owner_id, null);
    equal($(root).data('cardstories_table').game2table[0].ready_for_next_game, false);
});

test("init", 4, function() {
    var root = $(selector);
    var player_id = 1;
    var game_id = 30;

    root.cardstories_table(player_id, game_id);
    $.cardstories_table.load_game(player_id, game_id, {}, root);

    equal(get_keys($(root).data('cardstories_table').game2table).length, 1);
    equal($(root).data('cardstories_table').game2table[game_id].next_game_id, null);
    equal($(root).data('cardstories_table').game2table[game_id].next_owner_id, null);
    equal($(root).data('cardstories_table').game2table[game_id].ready_for_next_game, false);
});

// Init the table plugin without triggering reload.
init_table = function(player_id, game_id, root) {
    root.cardstories_table(player_id, game_id);
    $.cardstories_table.load_game(player_id, game_id, {}, root);
};

test("fetch_table_state", 4, function() {
    var root = $(selector);
    var player_id = 3;
    var game_id = 12;
    init_table(player_id, game_id, root);

    $.cardstories.ajax = function(options, _player_id, _game_id, _root) {
        equal(_player_id, player_id, 'ajax gets passed the player_id');
        equal(_game_id, game_id, 'ajax gets passed the game_id');
        equal(options.url, '../resource?action=state&type=table&modified=0&game_id='+game_id+'&player_id='+player_id);
        options.success([{table: 'fake state'}, {player: 'fake ignored info'}]);
    };

    $.cardstories_table.fetch_table_state(player_id, game_id, root, function(table_state) {
        deepEqual(table_state, {table: 'fake state'});
    });
});

test("get_available_game", 1, function() {
    var root = $(selector);
    var player_id = 2;
    var game_id = 13;
    var next_game_id = 712;
    init_table(player_id, game_id, root);

    var orig_fetch_table_state = $.cardstories_table.fetch_table_state;
    $.cardstories_table.fetch_table_state = function(_player_id, _game_id, _root, cb) {
        cb({next_game_id: next_game_id});
    };

    $.cardstories_table.get_available_game(player_id, root, function(_next_game_id) {
        equal(_next_game_id, next_game_id, 'callback gets passed the available game_id');
        $.cardstories_table.fetch_table_state = orig_fetch_table_state;
    });
});

test("force_state_update", 2, function() {
    var root = $(selector);
    var player_id = 1;
    var game_id = 15;
    var fake_data = {fake: 'table data'};
    init_table(player_id, game_id, root);

    var orig_fetch_table_state = $.cardstories_table.fetch_table_state;
    $.cardstories_table.fetch_table_state = function(_player_id, _game_id, _root, cb) {
        cb(fake_data);
    };

    var orig_state = $.cardstories_table.state;
    $.cardstories_table.state = function(_player_id, data, _root) {
        equal(_player_id, player_id, 'state gets passed the player_id');
        deepEqual(data, fake_data, 'state gets passed the table data');
        $.cardstories_table.state = orig_state;
        $.cardstories_table.fetch_table_state = orig_fetch_table_state;
    };

    $.cardstories_table.force_state_update(player_id, game_id, root);
});

test("state_next_as_author", 9, function() {
    var root = $(selector);
    var player_id = 1;
    var game_id = 15;
    init_table(player_id, game_id, root);

    // First get poll data
    var data = {type: 'table',
                player_id: player_id,
                game_id: game_id,
                next_game_id: null,
                next_owner_id: player_id};

    $.cardstories_table.state(player_id, data, root);
    equal($(root).data('cardstories_table').game2table[game_id].next_game_id, null);
    equal($(root).data('cardstories_table').game2table[game_id].next_owner_id, player_id);
    equal($(root).data('cardstories_table').game2table[game_id].ready_for_next_game, false);

    // Then reload when ready
    $.cardstories.reload = function(_player_id, _game_id, _options, _root) {
        equal(_player_id, player_id);
        equal(_game_id, undefined);
        equal(_options.previous_game_id, game_id);
        equal(_options.force_create, true);
    };

    $.cardstories_table.load_next_game_when_ready(true, player_id, game_id, root);
    equal($(root).data('cardstories_table').game2table[game_id].ready_for_next_game, true);

    equal($.cardstories_table.get_next_owner_id(player_id, game_id, root), player_id);
});

test("state_next_as_player", 7, function() {
    var root = $(selector);
    var player1 = 10;
    var player2 = 12
    var game1 = 15;
    var game2 = 17;
    init_table(player1, game1, root);

    // Ready before receiving next game data - wait
    equal($(root).data('cardstories_table').game2table[game1].ready_for_next_game, false);
    $.cardstories_table.load_next_game_when_ready(true, player1, game1, root);
    equal($(root).data('cardstories_table').game2table[game1].ready_for_next_game, true);

    // Reload as soon as next game_id is received in state info
    $.cardstories.reload = function(_player_id, next_game_id, _options, _root) {
        equal(_player_id, player1);
        equal(next_game_id, game2);
    };

    var data = {type: 'table',
                player_id: player1,
                game_id: game1,
                next_game_id: game2,
                next_owner_id: player2};
    $.cardstories_table.state(player1, data, root);
    equal($(root).data('cardstories_table').game2table[game1].next_game_id, game2);
    equal($(root).data('cardstories_table').game2table[game1].next_owner_id, player2);

    equal($.cardstories_table.get_next_owner_id(player1, game1, root), player2);
});

test("on_next_owner_change", 4, function() {
    var root = $(selector);
    var player1 = 10;
    var player2 = 12
    var game1 = 15;
    var game2 = 17;
    init_table(player1, game1, root);

    var data = {type: 'table',
            player_id: player1,
            game_id: game1,
            next_game_id: null,
            next_owner_id: player2};
    $.cardstories_table.state(player1, data, root);
    equal($(root).data('cardstories_table').game2table[game1].next_owner_id, player2);
    equal($(root).data('cardstories_table').game2table[game1].reset_callback, null);

    $.cardstories_table.on_next_owner_change(player1, game1, root, function(next_owner_id) {
        equal(next_owner_id, player1);
    })

    var data = {type: 'table',
            player_id: player1,
            game_id: game1,
            next_game_id: null,
            next_owner_id: player1};
    $.cardstories_table.state(player1, data, root);
    equal($(root).data('cardstories_table').game2table[game1].next_owner_id, player1);
});

