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

        tab_template: '<span class="cardstories_tab"><span class="cardstories_tab_status"></span> <a class="cardstories_tab_title"></a> <a class="cardstories_tab_close"></a>',

        init: function(player_id, current_game_id, root) {
            // Don't initialize twice.
            if ($(root).data('cardstories_tabs')) {
                return;
            }
            var element = $('.cardstories_tabs', root);
            // Save data for later use.
            $(root).data('cardstories_tabs', {
                element: element,
                tab_states: {},
                current_game_id: current_game_id
            });
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

                title.text(game.sentence);

                if (!is_current) {
                    title.attr('href', $.cardstories.reload_link(game.id));
                    // TODO: The button will probably be an image.
                    close_btn.html('&#10005;'); // a cross.
                    close_btn.click(function() {
                        $this.remove_tab(tab, player_id, game.id);
                    });

                    // TODO: The status will need to be redone, it will probably be implemented
                    // with a class and an associated color.
                    if ($this.requires_action(player_id, game, root)) {
                        status.text('*');
                    } else {
                        status.text('');
                    }
                }

                // TODO: Remove, this is purely temorary!
                tab.css({
                    padding: '6px',
                    margin: '3px',
                    backgroundColor: is_current ? 'transparent' : '#ddd',
                    cursor: 'pointer'
                });

                element.append(tab);
            });
        },

        // Removes the tab from the page, and issues an ajax call to remove
        // the tab on the webservice.
        remove_tab: function(tab, player_id, game_id) {
            tab.remove(); // remove the tab from the DOM.
            $.cardstories.send({
                action: 'remove_tab',
                game_id: game_id,
                player_id: player_id
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
                    if (game.players.length === 1) { // no player joined yet
                        requires = true;
                    } else if (game.ready) { // game can be moved to the voting phase
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

    $.fn.cardstories_tabs = function(player_id, game_id) {
        $.cardstories_tabs.init(player_id, game_id, this);
        return this;
    };

    // Register cardstories plugin.
    $.cardstories.register_plugin($.cardstories_tabs);

})(jQuery);
