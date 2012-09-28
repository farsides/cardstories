$.fx.off = true;

var selector = '#cardstories_tabs_example';
var orig_requires_action = $.cardstories_tabs.requires_action;

function setup() {
    $.cardstories.send = function() { throw 'Please rebind $.cardstories.send'; };
    $.cardstories.reload = function() { throw 'Please rebind $.cardstories.reload'; };
    $.cardstories_tabs.requires_action = orig_requires_action;
}

module("cardstories_tabs", {setup: setup});

test("state", 39, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 899;
    var game_id = 12;

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    equal(element.find('.cardstories_tab').length, 0, 'There are no tabs initially');

    var games = [
        {id: 101, sentence: 'SENTENCE1', state: 'invitation'},
        {id: 102, sentence: 'SENTENCE2', state: 'vote'},
        {id: 103, sentence: null, state: 'create'},
        {id: 104, sentence: 'SENTENCE4', state: 'pick'},
        {id: 105, sentence: null, state: 'canceled'},
        {id: 106, sentence: 'SENTENCE6', state: 'canceled'}
    ];
    var tabs;

    $.cardstories_tabs.requires_action = function(_player_id, game, _root) {
        equal(_player_id, player_id, 'requires_action gets passed player_id');
        ok(game.state, 'requires_action gets passed the game');
        equal(_root.attr('id'), 'cardstories_tabs_example', 'requires_action gets passed the root');
        return false;
    };

    $.cardstories_tabs.state(player_id, {games: games}, root);
    tabs = element.find('.cardstories_tab');
    equal(tabs.length, 6, 'Six tabs are created');
    ok(tabs.eq(0).text().match('SENTENCE1'));
    ok(tabs.eq(1).text().match('SENTENCE2'));
    ok(tabs.eq(2).text().match('New game')); // For game in 'create' state, 'New game' is shown.
    ok(tabs.eq(3).text().match('SENTENCE4'));
    ok(tabs.eq(4).text().match('New game')); // For game in 'canceled' state, without a sentence, 'New game' is shown.
    ok(tabs.eq(5).text().match('SENTENCE6'));

    // Call state again without some of the games.
    games = [
        {id: 101, sentence: 'SENTENCE1', state: 'invitation'},
        {id: 103, sentence: null, state: 'create'},
        {id: 104, sentence: 'SENTENCE4', state: 'pick'}
    ];

    $.cardstories_tabs.state(player_id, {games: games}, root);
    tabs = element.find('.cardstories_tab');
    equal(tabs.length, 3, 'Three tabs are created');
    ok(tabs.eq(0).text().match('SENTENCE1'));
    ok(tabs.eq(1).text().match('New game'));
    ok(tabs.eq(2).text().match('SENTENCE4'));
});

test("Tabs are links to games", 2, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 102;
    var game_id = 124;
    var tab_game_id = 11111;
    var games = [
        {id: tab_game_id, sentence: 'SENTENCE'}
    ];

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);
    $.cardstories_tabs.state(player_id, {games: games}, root);

    var tab = $('.cardstories_tab', element);
    equal(tab.length, 1, 'There is one tab');
    var tabs = tab.find('a.cardstories_tab_title');
    ok(tabs.eq(0).attr('href').match('game_id=' + tab_game_id), 'tab contains link to game');
});

test("get_open_game_ids", 12, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 499;
    var game_id = 52;

    $.cardstories_tabs.requires_action = function(player_id, game, root) { return false; };

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    equal($.cardstories_tabs.get_open_game_ids(root).length, 0, 'There are no open tabs initially');

    var games = [
        {id: 101, sentence: 'SENTENCE1', state: 'invitation'},
        {id: 102, sentence: 'SENTENCE2', state: 'vote'},
        {id: 103, sentence: null, state: 'create'},
        {id: 104, sentence: 'SENTENCE4', state: 'pick'},
        {id: 105, sentence: null, state: 'canceled'},
        {id: 106, sentence: 'SENTENCE6', state: 'canceled'}
    ];
    var tabs;

    $.cardstories_tabs.state(player_id, {games: games}, root);
    var game_ids = $.cardstories_tabs.get_open_game_ids(root);
    equal(game_ids.length, 6, 'Six games are open in tabs');
    equal(game_ids[0], 101);
    equal(game_ids[1], 102);
    equal(game_ids[2], 103);
    equal(game_ids[3], 104);
    equal(game_ids[4], 105);
    equal(game_ids[5], 106);

    // Call state again without some of the games.
    games = [
        {id: 101, sentence: 'SENTENCE1', state: 'invitation'},
        {id: 103, sentence: null, state: 'create'},
        {id: 104, sentence: 'SENTENCE4', state: 'pick'}
    ];

    $.cardstories_tabs.state(player_id, {games: games}, root);
    var game_ids = $.cardstories_tabs.get_open_game_ids(root);
    equal(game_ids.length, 3, 'Three games are open in tabs');
    equal(game_ids[0], 101);
    equal(game_ids[1], 103);
    equal(game_ids[2], 104);
});

test("closing an unfocused tab", 7, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 111;
    var game_id = 101;
    var games = [
        {id: 1, sentence: 'SENTENCE'},
        {id: game_id, sentence: 'FOCUSED SENTENCE'}
    ];

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);
    $.cardstories_tabs.state(player_id, {games: games}, root);
    equal($('.cardstories_tab', element).length, 2, 'There are two tabs');

    // Click the close button.
    // The tab should be removed from the DOM and the 'close_tab_action' call
    // issued to the service.
    $.cardstories.send = function(query, cb, _player_id, _game_id, root, opts) {
        equal(_player_id, player_id, 'player_id is passed to the send function');
        equal(_game_id, game_id, 'game_id is passed to the send function');
        equal(query.action, 'close_tab_action', 'close_tab_action call is issued');
        equal(query.player_id, player_id, 'player_id is passed to the service');
        equal(query.game_id, games[0].id, 'game_id is passed to the service');
        return $.Deferred().resolve();
    };
    var first_tab = $('.cardstories_tab', element).eq(0);
    $('.cardstories_tab_close', first_tab).click();
    equal($('.cardstories_tab', element).length, 1, 'There is one tab left');
});

test("closing the currently focused tab with tabs to the right", 9, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 111;
    var game_id = 3;
    var games = [
        {id: 1, sentence: 'SENTENCE1'},
        {id: 2, sentence: 'SENTENCE2'},
        {id: 3, sentence: 'SENTENCE3'},
        {id: 4, sentence: 'SENTENCE4'},
        {id: 5, sentence: 'SENTENCE5'}
    ];

    $.cardstories.send = function(query, cb, _player_id, _game_id, root, opts) {
        equal(_player_id, player_id, 'player_id is passed to the send function');
        equal(_game_id, game_id, 'game_id is passed to the send function');
        equal(query.action, 'close_tab_action', 'close_tab_action call is issued');
        equal(query.player_id, player_id, 'player_id is passed to the service');
        ok(query.game_id, 'game_id is passed to the service');
        return $.Deferred().resolve();
    };

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    // When there are tabs to right and left of current tab,
    // it will load the first on one the right.
    $.cardstories_tabs.state(player_id, {games: games}, root);
    equal($('.cardstories_tab', element).length, 5, 'There are five tabs');

    // Click the close button.
    // The tab should be removed from the DOM, the 'close_tab_action' call
    // issued to the service, and game nr. 4 loaded.
    $.cardstories.reload = function(_player_id, _game_id, _options, _root) {
        equal(_player_id, player_id, 'reload gets passed the player_id');
        equal(_game_id, 4, 'game nr. 4 is loaded');
    };
    var tab3 = $('.cardstories_tab', element).eq(2);
    tab3.find('.cardstories_tab_close').click();
    equal($('.cardstories_tab', element).length, 4, 'There are four tabs');
});

test("closing the currently focused tab with tabs to the left", 9, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 111;
    var game_id = 3;
    var games = [
        {id: 1, sentence: 'SENTENCE1'},
        {id: 2, sentence: 'SENTENCE2'},
        {id: 3, sentence: 'SENTENCE3'}
    ];

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    $.cardstories.send = function(query, cb, _player_id, _game_id, root, opts) {
        equal(_player_id, player_id, 'player_id is passed to the send function');
        equal(_game_id, game_id, 'game_id is passed to the send function');
        equal(query.action, 'close_tab_action', 'close_tab_action call is issued');
        equal(query.player_id, player_id, 'player_id is passed to the service');
        ok(query.game_id, 'game_id is passed to the service');
        return $.Deferred().resolve();
    };

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    // When there are tabs to the left, but no tabs to the right of current tab,
    // it will load the first one on the left.
    $.cardstories_tabs.state(player_id, {games: games}, root);
    equal($('.cardstories_tab', element).length, 3, 'There are three tabs');

    // Click the close button.
    // The tab should be removed from the DOM, the 'close_tab_action' call
    // issued to the service, and game nr. 2 loaded.
    $.cardstories.reload = function(_player_id, _game_id, _options, _root) {
        equal(_player_id, player_id, 'reload gets passed the player_id');
        equal(_game_id, 2, 'Game nr. 2 is loaded');
    };
    var tab = $('.cardstories_tab', element).last();
    tab.find('.cardstories_tab_close').click();
    equal($('.cardstories_tab', element).length, 2, 'There are two tabs left');
});

test("closing the currently focused tab when it is the only tab", 9, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 111;
    var game_id = 3;
    var games = [
        {id: 3, sentence: 'SENTENCE3'}
    ];

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    $.cardstories.send = function(query, cb, _player_id, _game_id, root, opts) {
        equal(_player_id, player_id, 'player_id is passed to the send function');
        equal(_game_id, game_id, 'game_id is passed to the send function');
        equal(query.action, 'close_tab_action', 'close_tab_action call is issued');
        equal(query.player_id, player_id, 'player_id is passed to the service');
        ok(query.game_id, 'game_id is passed to the service');
        return $.Deferred().resolve();
    };

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    // When this is the only tab left, it will open a 'New Game' tab.
    $.cardstories_tabs.state(player_id, {games: games}, root);
    equal($('.cardstories_tab', element).length, 1, 'There is one tab');

    // Click the close button.
    // The tab should be removed from the DOM, the 'close_tab_action' call
    // issued to the service, and 'New game' tab loaded.
    $.cardstories.reload = function(_player_id, _game_id, _options, _root) {
        equal(_player_id, player_id, 'reload gets passed the player_id');
        strictEqual(_game_id, undefined, 'New game tab is loaded');
    };
    var tab = $('.cardstories_tab', element).last();
    tab.find('.cardstories_tab_close').click();
    equal($('.cardstories_tab', element).length, 0, 'There are no tabs left');
});

test("close_tab_for_game", 9, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 111;
    var game_id = 3;
    var games = [
        {id: 1, sentence: 'SENTENCE1'},
        {id: 2, sentence: 'SENTENCE2'},
        {id: 3, sentence: 'SENTENCE3'}
    ];

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    $.cardstories.send = function(query, cb, _player_id, _game_id, root, opts) {
        equal(_player_id, player_id, 'player_id is passed to the send function');
        equal(_game_id, game_id, 'game_id is passed to the send function');
        equal(query.action, 'close_tab_action', 'close_tab_action call is issued');
        equal(query.player_id, player_id, 'player_id is passed to the service');
        ok(query.game_id, 'game_id is passed to the service');
        return $.Deferred().resolve();
    };

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    $.cardstories_tabs.state(player_id, {games: games}, root);
    equal($('.cardstories_tab', element).length, 3, 'There are three tabs');

    // Remove the tab programmatically by passing the game_id.
    // The tab should be removed from the DOM and the 'close_tab_action' call
    // issued to the service.
    var game_to_remove_id = 2;
    $.cardstories_tabs.close_tab_for_game(game_to_remove_id, player_id, root, function() {
        var tabs = $('.cardstories_tab', element);
        equal(tabs.length, 2, 'There are two tabs left');
        equal(tabs.eq(0).text(), 'SENTENCE1', 'First game tab exists');
        equal(tabs.eq(1).text(), 'SENTENCE3', 'Third game tab exists');
    });
});

test("requires_action author", 12, function() {
    var root = $(selector);
    var player_id = 102;
    var game_id = 1002;
    root.cardstories_tabs(player_id, game_id);

    function does_require_action(game_attrs) {
        var defaults = {
            id: game_id,
            owner: true
        };
        var game = $.extend(defaults, game_attrs);
        return $.cardstories_tabs.requires_action(player_id, game, root);
    }

    // Requires action when in create state.
    ok(does_require_action({state: 'create'}));
    // Doesn't require action if in invitation state and there are no players
    ok(!does_require_action({state: 'invitation',
                            players: [{player_id: 'the owner'}],
                            ready: false}));
    // Doesn't require action if in invitation state and there are players, but game is not ready yet.
    ok(!does_require_action({state: 'invitation',
                             players: [{player_id: 1}, {player_id: 2}],
                             ready: false}));
    // Requires action if in invitation state and game is ready to move on.
    ok(does_require_action({state: 'invitation',
                            players: [{player_id: 1}, {player_id: 2}, {player_id: 3}],
                            ready: true}));
    // Doesn't require action if in vote state and game is not ready.
    ok(!does_require_action({state: 'vote',
                             players: [{player_id: 1}, {player_id: 2}, {player_id: 3}],
                             ready: false}));
    // Requires action if in vote state and game is ready.
    ok(does_require_action({state: 'vote',
                            players: [{player_id: 1}, {player_id: 2}, {player_id: 3}],
                            ready: true}));
    // Requires action when game moves into complete state.
    ok(does_require_action({state: 'complete',
                            players: [{player_id: 1}, {player_id: 2}, {player_id: 3}]}));
    // Doesn't require action if game is in the complete state, but has been there already.
    ok(!does_require_action({state: 'complete'}));
    // Requires action when in complete state and player is the next owner.
    ok(does_require_action({state: 'complete',
                            next_owner_id: player_id,
                            self: [31, 33, 'y']}));
    // Doesn't require action when in complete state and player is not the next owner.
    ok(!does_require_action({state: 'complete',
                             next_owner_id: player_id + 1,
                             self: [31, 33, 'y']}));
    // Requires action when in complete state and next game is ready.
    ok(does_require_action({state: 'complete',
                            next_game_id: game_id + 1,
                            self: [31, 33, 'y']}));
    // Does not require action when next_game_id equals current game id.
    ok(!does_require_action({state: 'complete',
                             next_game_id: game_id,
                             self: [31, 33, 'y']}));
});

test("requires_action player", 11, function() {
    var root = $(selector);
    var player_id = 102;
    var game_id = 1002;
    root.cardstories_tabs(player_id, game_id);

    function does_require_action(game_attrs) {
        var defaults = {
            id: game_id,
            owner: false
        };
        var game = $.extend(defaults, game_attrs);
        return $.cardstories_tabs.requires_action(player_id, game, root);
    }

    // Doesn't require action in create state (that's the authors responsibility).
    ok(!does_require_action({state: 'create',
                             self: [null, null, null]}));
    // Requires action if in invitation state and didn't pick a card yet.
    ok(does_require_action({state: 'invitation',
                            self: [null, null, null]}));
    // Doesn't require action if in invitation state and already picked a card.
    ok(!does_require_action({state: 'invitation',
                             self: [31, null, null]}));
    // Requires action if in vote state and didn't vote yet.
    ok(does_require_action({state: 'vote',
                            self: [31, null, null]}));
    // Doesn't require action if in vote state and already voted.
    ok(!does_require_action({state: 'vote',
                             self: [31, 33, null]}));
    // Requires action when game moves into complete state.
    ok(does_require_action({state: 'complete',
                            self: [31, 33, 'y']}));
    // Doesn't require action if game is in the complete state, but has been there already.
    ok(!does_require_action({state: 'complete'}));
    // Requires action when in complete state and player is the next owner.
    ok(does_require_action({state: 'complete',
                            next_owner_id: player_id,
                            self: [31, 33, 'y']}));
    // Doesn't require action when in complete state and player is not the next owner.
    ok(!does_require_action({state: 'complete',
                             next_owner_id: player_id + 1,
                             self: [31, 33, 'y']}));
    // Requires action when in complete state and next game is ready.
    ok(does_require_action({state: 'complete',
                            next_game_id: game_id + 1,
                            self: [31, 33, 'y']}));
    // Does not require action when next_game_id equals current game id.
    ok(!does_require_action({state: 'complete',
                             next_game_id: game_id,
                             self: [31, 33, 'y']}));
});

