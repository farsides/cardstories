//
//     Copyright (C) 2011 Farsides <contact@farsides.com>
//
//     Authors:
//              Matjaz Gregoric <gremat@gmail.com>
//
//     This program is free software: you can redistribute it and/or modify
//     it under the terms of the GNU General Public License as published by
//     the Free Software Foundation, either version 3 of the License, or
//     (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
//
//     You should have received a copy of the GNU General Public License
//     along with this program.  If not, see <http://www.gnu.org/licenses/>.
//
(function($) {

    $.cardstories_tabs = {

        name: 'tabs',

        poll: true,

        tab_template: '<li class="cardstories_tab"><a class="cardstories_tab_title"></a><a class="cardstories_tab_close"><img src="/static/css/images/tab_close.png" /></a></li>',

        new_game_tab_template: '<li class="cardstories_new"><a class="cardstories_tab_title" title="Create a new game!"><img src="/static/css/images/tab_new.png" /></a></li>',

        init: function(player_id, game_id, root) {
            // Save data for later use.
            $(root).data('cardstories_tabs', {
                tab_states: {},
                element: null,        // These two will be
                current_game_id: null // popuplated by 'load_game'.
            });
        },

        load_game: function(player_id, game_id, options, root) {
            var data = $(root).data('cardstories_tabs');
            data.current_game_id = game_id;
            data.element = $('.cardstories_tabs', root);
        },

        // When called, the currently rendered tabs are wiped out, and re-rendered from the
        // game objects in the data parameter.
        // While reconstructing the tabs every time isn't the most efficient, it is simple to
        // implement, and doesn't seem to cause performance issues.
        state: function(player_id, data, root) {
            var $this = this;
            var games = data.games;
            var root_data = $(root).data('cardstories_tabs');
            var element = root_data.element;
            var current_game_id = root_data.current_game_id;

            // Wipe out the tabs.
            element.empty();

            // If current game_id is undefined (the player is creating a new game),
            // add a dynamically created "New game" tab.
            if (!current_game_id) {
                games.push({id: 'new', sentence: 'New game'});
            }

            // And repaint them.
            $.each(games, function(i, game) {
                var tab = $($this.tab_template);
                var title = $('.cardstories_tab_title', tab);
                var status = $('.cardstories_tab_status', tab);
                var close_btn = $('.cardstories_tab_close', tab);
                var is_current = game.id === 'new' || game.id === current_game_id;

                title.text(game.sentence.substring(0, 15));
                tab.data('game_id', game.id);

                if (is_current) {
                    tab.addClass('cardstories_selected');
                    close_btn.click(function() {
                        $this.remove_current_tab(tab, player_id, current_game_id, root);
                    });
                } else {
                    title.attr('href', $.cardstories.reload_link(game.id, {}));
                    title.click(function() {
                        $.cardstories.reload(player_id, game.id, {}, root);
                        return false;
                    });
                    close_btn.click(function() {
                        $this.remove_tab(tab, player_id, game.id);
                    });

                    if ($this.requires_action(player_id, game, root)) {
                        tab.addClass('cardstories_ready');
                    }
                }

                element.append(tab);
            });

            // Add the tab to create a new game
            var new_game_tab = $($this.new_game_tab_template);
            var new_game_link = new_game_tab.find('a');
            var new_game_href = $.cardstories.reload_link(undefined, {force_create: true});
            new_game_link.attr('href', new_game_href);
            new_game_link.bind('click', function() {
                $.cardstories.reload(player_id, undefined, {force_create: true}, root);
                return false;
            });
            element.append(new_game_tab);

            // Workaround for Chrome 17 bug: http://code.google.com/p/chromium/issues/detail?id=111218
            // Without this hack, the deck sometimes disappears, especially in Chrome 17 on OS X.
            // See: http://tickets.farsides.com/issues/821
            // TODO: Remove when Chrome bug is fixed and this isn't needed anymore.
            if (window.chrome) {
                $('.cardstories_deck', root).hide().show();
            }
        },

        // Removes the current tab from the page and loads game from one of the other
        // open tabs. If this is the last opened tab, it opens a 'New game' tab instead.
        remove_current_tab: function(tab, player_id, game_id, root) {
            // After removing this tab, do one of the following:
            //  - If there are tabs on the right side of this tab,
            //    load the first one on the right.
            //  - If there are tabs on the left, load the first on on the left.
            //  - Load a 'New game' tab.

            // ID of game to open after closing this tab. game_id of undefined
            // means create a new game.
            var next_game_id;
            var next_tab = tab.next('.cardstories_tab');
            var prev_tab = tab.prev('.cardstories_tab');
            if (next_tab.length) {
                next_game_id = next_tab.data('game_id');
            } else if (prev_tab.length) {
                next_game_id = prev_tab.data('game_id');
            }

            this.remove_tab(tab, player_id, game_id, function() {
                $.cardstories.reload(player_id, next_game_id, {force_create: !next_game_id}, root);
            });
        },

        // Removes the tab from the page, and issues an ajax call to remove
        // the tab on the webservice.
        remove_tab: function(tab, player_id, game_id, cb) {
            var promise;
            if (game_id) {
                promise = $.cardstories.send({
                    action: 'remove_tab',
                    game_id: game_id,
                    player_id: player_id
                });
            } else {
                promise = $.Deferred().resolve();
            }

            // remove the tab from the DOM.
            tab.fadeOut(function() {
                tab.remove();
                promise.done(function() {
                    if (cb) {
                        cb();
                    }
                });
            });
        },

        // Returns true if the game passed in as the second parameter requires action
        // (the tabs that hold games that require action are rendered differently).
        // The rules for when a tab is said to require action will probably change a bit
        // in the future as we discover what works best in practice.
        requires_action: function(player_id, game, root) {
            var requires = false;
            var tab_states = $(root).data('cardstories_tabs').tab_states;
            var previous_state = tab_states[game.id];
            var new_state = game.state;
            tab_states[game.id] = new_state;
            
            if (previous_state && previous_state !== new_state) { // the state has changed
                if (new_state === 'complete') { // the results have been announced
                    requires = true;
                }
            }
            if (game.owner) {
                if (new_state === 'invitation') {
                    if (game.ready) { // game can be moved to the voting phase
                        requires = true;
                    }
                } else if (new_state === 'vote') {
                    if (game.ready) { // game can be moved to the results phase
                        requires = true;
                    }
                }
            } else {
                if (new_state === 'invitation') {
                    if (!game.self[0]) { // didn't pick yet
                        requires = true;
                    }
                } else if (new_state === 'vote') {
                    if (game.self && !game.self[1]) { // didn't vote yet
                        requires = true;
                    }
                }
            }
            return requires;
        }
    };

    $.fn.cardstories_tabs = function(player_id) {
        $.cardstories_tabs.init(player_id, null, this);
        return this;
    };

    // Register cardstories plugin.
    $.cardstories.register_plugin($.cardstories_tabs);

})(jQuery);
