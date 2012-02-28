$.fx.off = true;

var selector = '#cardstories_tabs_example';
var orig_requires_action = $.cardstories_tabs.requires_action;

function setup() {
    $.cardstories.send = function() { throw 'Please rebind $.cardstories.send'; };
    $.cardstories.reload = function() { throw 'Please rebind $.cardstories.reload'; };
    $.cardstories_tabs.requires_action = orig_requires_action;
}

module("cardstories_tabs", {setup: setup});

test("state", 31, function() {
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
        {id: 104, sentence: 'SENTENCE4', state: 'pick'}
    ];
    var tabs;

    $.cardstories_tabs.requires_action = function(_player_id, game, _root) {
        equal(_player_id, player_id, 'requires_action gets passed player_id');
        ok(game.state, 'requires_action gets passed the game');
        equal(_root.attr('id'), 'cardstories_tabs_example', 'requires_action gets passed the root')
        return false;
    };

    $.cardstories_tabs.state(player_id, {games: games}, root);
    tabs = element.find('.cardstories_tab');
    equal(tabs.length, 4, 'Four tabs are created');
    ok(tabs.eq(0).text().match('SENTENCE1'));
    ok(tabs.eq(1).text().match('SENTENCE2'));
    ok(tabs.eq(2).text().match('New game')); // For game in 'create' state, 'New game' is shown.
    ok(tabs.eq(3).text().match('SENTENCE4'));

    // Call state again without the second game.
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

test("closing an unfocused tab", 5, function() {
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
    // The tab should be removed from the DOM and the 'remove_tab' call
    // issued to the service.
    $.cardstories.send = function(query) {
        equal(query.action, 'remove_tab', 'remove_tab call is issued');
        equal(query.player_id, player_id, 'player_id is passed to the service');
        equal(query.game_id, games[0].id, 'game_id is passed to the service');
        return $.Deferred().resolve();
    };
    var first_tab = $('.cardstories_tab', element).eq(0);
    $('.cardstories_tab_close', first_tab).click();
    equal($('.cardstories_tab', element).length, 1, 'There is one tab left');
});

test("closing the currently focused tab with tabs to the right", 7, function() {
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

    $.cardstories.send = function(query) {
        equal(query.action, 'remove_tab', 'remove_tab call is issued');
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
    // The tab should be removed from the DOM, the 'remove_tab' call
    // issued to the service, and game nr. 4 loaded.
    $.cardstories.reload = function(_player_id, _game_id, _options, _root) {
        equal(_player_id, player_id, 'reload gets passed the player_id');
        equal(_game_id, 4, 'game nr. 4 is loaded');
    };
    var tab3 = $('.cardstories_tab', element).eq(2);
    tab3.find('.cardstories_tab_close').click();
    equal($('.cardstories_tab', element).length, 4, 'There are four tabs');
});

test("closing the currently focused tab with tabs to the left", 7, function() {
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

    $.cardstories.send = function(query) {
        equal(query.action, 'remove_tab', 'remove_tab call is issued');
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
    // The tab should be removed from the DOM, the 'remove_tab' call
    // issued to the service, and game nr. 2 loaded.
    $.cardstories.reload = function(_player_id, _game_id, _options, _root) {
        equal(_player_id, player_id, 'reload gets passed the player_id');
        equal(_game_id, 2, 'Game nr. 2 is loaded');
    };
    var tab = $('.cardstories_tab', element).last();
    tab.find('.cardstories_tab_close').click();
    equal($('.cardstories_tab', element).length, 2, 'There are two tabs left');
});

test("closing the currently focused tab when it is the only tab", 7, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 111;
    var game_id = 3;
    var games = [
        {id: 3, sentence: 'SENTENCE3'}
    ];

    root.cardstories_tabs(player_id);
    $.cardstories_tabs.load_game(player_id, game_id, {}, root);

    $.cardstories.send = function(query) {
        equal(query.action, 'remove_tab', 'remove_tab call is issued');
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
    // The tab should be removed from the DOM, the 'remove_tab' call
    // issued to the service, and 'New game' tab loaded.
    $.cardstories.reload = function(_player_id, _game_id, _options, _root) {
        equal(_player_id, player_id, 'reload gets passed the player_id');
        strictEqual(_game_id, undefined, 'New game tab is loaded');
    };
    var tab = $('.cardstories_tab', element).last();
    tab.find('.cardstories_tab_close').click();
    equal($('.cardstories_tab', element).length, 0, 'There are no tabs left');
});

test("requires_action author", 7, function() {
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

    // Doesn't require action if game is in the complete state.
    ok(!does_require_action({state: 'complete'}));
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
});

test("requires_action player", 6, function() {
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

    // Doesn't require action if game is in the complete state.
    ok(!does_require_action({state: 'complete'}));
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
});

