var selector = '#cardstories_tabs_example';
var orig_requires_action = $.cardstories_tabs.requires_action;

function setup() {
    $.cardstories.send = function() { throw 'Please rebind $.cardstories.send'; };
    $.cardstories_tabs.requires_action = orig_requires_action;
}

module("cardstories_tabs", {setup: setup});

test("state", 25, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 899;
    var game_id = 12;

    root.cardstories_tabs(player_id, game_id);

    equal(element.find('.cardstories_tab').length, 0, 'There are no tabs initially');

    var games = [
        {id: 101, sentence: 'SENTENCE1', state: 'invitation'},
        {id: 102, sentence: 'SENTENCE2', state: 'vote'},
        {id: 103, sentence: 'SENTENCE3', state: 'pick'}
    ];
    var tabs;

    $.cardstories_tabs.requires_action = function(_player_id, game, _root) {
        equal(_player_id, player_id, 'requires_action gets passed player_id');
        equal(game.sentence.substring(0, 8), 'SENTENCE');
        equal(_root.attr('id'), 'cardstories_tabs_example', 'requires_action gets passed the root')
        return false;
    };

    $.cardstories_tabs.state(player_id, {games: games}, root);
    tabs = element.find('.cardstories_tab');
    equal(tabs.length, 4, 'Four tabs are created (3 games + new game)');
    ok(tabs.eq(0).text().match('SENTENCE1'));
    ok(tabs.eq(1).text().match('SENTENCE2'));
    ok(tabs.eq(2).text().match('SENTENCE3'));
    ok(tabs.eq(3).attr('class').match('cardstories_tab cardstories_new'));

    // Call state again without the second game.
    games = [
        {id: 101, sentence: 'SENTENCE1', state: 'invitation'},
        {id: 103, sentence: 'SENTENCE3', state: 'pick'}
    ];

    $.cardstories_tabs.state(player_id, {games: games}, root);
    tabs = element.find('.cardstories_tab');
    equal(tabs.length, 3, 'Three tabs are created');
    ok(tabs.eq(0).text().match('SENTENCE1'));
    ok(tabs.eq(1).text().match('SENTENCE3'));
    ok(tabs.eq(2).attr('class').match('cardstories_tab cardstories_new'));
});

test("Tabs are links to games", 3, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 102;
    var game_id = 124;
    var tab_game_id = 11111;
    var games = [
        {id: tab_game_id, sentence: 'SENTENCE'}
    ];

    root.cardstories_tabs(player_id, game_id);

    $.cardstories_tabs.state(player_id, {games: games}, root);

    var tab = $('.cardstories_tab', element);
    equal(tab.length, 2, 'There are two tabs');
    var tabs = tab.find('a.cardstories_tab_title');
    ok(tabs.eq(0).attr('href').match('game_id=' + tab_game_id), 'tab contains link to game');
    equal(tabs.eq(1).attr('href'), '?create=1', 'tab contains link to create a new game');
});

test("closing a tab", 5, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 111;
    var game_id = 101;
    var games = [
        {id: 1, sentence: 'SENTENCE'}
    ];

    root.cardstories_tabs(player_id, game_id);

    $.cardstories_tabs.state(player_id, {games: games}, root);
    equal($('.cardstories_tab', element).length, 2, 'There are two tabs');

    // Click the close button.
    // The tab should be removed from the DOM and the 'remove_tab' call
    // issued to the service.
    $.cardstories.send = function(query) {
        equal(query.action, 'remove_tab', 'remove_tab call is issued');
        equal(query.player_id, player_id, 'player_id is passed to the service');
        equal(query.game_id, games[0].id, 'game_id is passed to the service');
    };
    $('.cardstories_tab_close', element).click();
    equal($('.cardstories_tab', element).length, 1, 'There is one tab');
});

test("dynamic tab for new game", 3, function() {
    var root = $(selector);
    var element = $('.cardstories_tabs', root);
    var player_id = 121;
    var game_id = undefined; // game_id is undefined when creating a new game.
    var other_game_id = 1001;
    var other_game_title = 'The Other Game';
    var games = [
        {id: other_game_id, sentence: other_game_title}
    ];

    root.cardstories_tabs(player_id, game_id);

    $.cardstories_tabs.state(player_id, {games: games}, root);
    // There is one tab for game 1001, and one created dynamically for the new game
    var tabs = $('.cardstories_tab', element);
    equal(tabs.length, 3, 'A fake tab for new game has been created');
    equal(tabs.eq(0).find('.cardstories_tab_title').text(), other_game_title);
    ok(tabs.eq(1).find('.cardstories_tab_title').text().match(/new game/i));
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
    // Requires action if in invitation state and there are no players (just the GM).
    ok(does_require_action({state: 'invitation',
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

