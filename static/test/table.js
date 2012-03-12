var selector = '#cardstories_root';
var default_query_get = $.query.get;
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

    $.query.get = function() { throw 'Please rebind "$.query.get"'; };
    $.cardstories.ajax = function() { throw 'Please rebind "ajax"'; };
    $.cardstories.reload = function() { throw 'Please rebind "reload"'; };

    $.cardstories_table.force_state_update = default_cardstories_table_force_state_update;
}

module("cardstories_table", {setup: setup});

test("init_create", 4, function() {
    var root = $(selector);
    var player_id = 1;

    $.query.get = function(param_name) {
        if(param_name == 'create') { return true; };
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

test("init_game_id", 4, function() {
    var root = $(selector);
    var player_id = 1;
    var game_id = 30;

    $.query.get = function(param_name) {
        if(param_name == 'create') { return false; };
    };
    $.cardstories_table.force_state_update = function(_player_id, _game_id, _root) {
        ok(false, "Plugin shouldn't intervene when a game_id is explicitly requested");
    };

    root.cardstories_table(player_id, game_id);
    $.cardstories_table.load_game(player_id, game_id, {}, root);

    equal(get_keys($(root).data('cardstories_table').game2table).length, 1);
    equal($(root).data('cardstories_table').game2table[game_id].next_game_id, null);
    equal($(root).data('cardstories_table').game2table[game_id].next_owner_id, null);
    equal($(root).data('cardstories_table').game2table[game_id].ready_for_next_game, false);
});

/* TODO: Re-activate, maybe move
   -----
test("init_find_game", 4, function() {
    var root = $(selector);
    var player_id = 1;
    var game_id = undefined;

    $.query.get = function(param_name) {
        if(param_name == 'create') { return false; };
    };
    $.cardstories_table.force_state_update = function(_player_id, _game_id, _root) {
        // Should request a game to join when no game specified nor create
        equal(player_id, _player_id);
        equal(game_id, _game_id);
    };

    root.cardstories_table(player_id, game_id);

    var game2table = root.data('cardstories_table').game2table;
    equal(get_keys(game2table).length, 1);
    equal(game2table[0].ready_for_next_game, true);
});

test("init_find_game_as_author_already_created", 5, function() {
    var root = $(selector);
    var player_id = 1;
    var game_id = 15;

    $.query.get = function(param_name) {
        if(param_name == 'create') { return false; };
    };
    $.cardstories.ajax = function(options) {
        // Should request a game to join
        var query = {
                action: 'state',
                type: 'table',
                modified: 0,
                game_id: undefined,
                player_id: player_id,
        }

        equal(options.url, $.cardstories.url + '?' + $.param(query, true));

        // Author of a game joins again after having created the game
        var data = {type: 'table',
                    player_id: player_id,
                    game_id: null,
                    next_game_id: game_id,
                    next_owner_id: player_id};
        options.success(data);
    };
    // Should be redirected to the game he created (and not to game creation)
    $.cardstories.reload = function(_player_id, _game_id, _options, _root) {
        equal(_player_id, player_id);
        equal(_game_id, game_id);
    };

    root.cardstories_table(player_id, undefined, root);

    var game2table = root.data('cardstories_table').game2table;
    equal(get_keys(game2table).length, 1);
    equal(game2table[0].ready_for_next_game, true);
});
*/

// Init the table plugin without triggering reload
init_table = function(player_id, game_id, root) {
    $.query.get = function(param_name) {
        if(param_name == 'create') { return false; };
    };
    root.cardstories_table(player_id, game_id);
    $.cardstories_table.load_game(player_id, game_id, {}, root);
};

test("force_state_update", 1, function() {
    var root = $(selector);
    var player_id = 1;
    var game_id = 15;
    init_table(player_id, game_id, root);

    $.cardstories.ajax = function(options) {
        equal(options.url, '../resource?action=state&type=table&modified=0&game_id='+game_id+'&player_id='+player_id);
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

