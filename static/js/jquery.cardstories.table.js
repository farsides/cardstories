//
//  Copyright (C) 2012 Farsides <contact@farsides.com>
//
//  Authors:
//          Xavier Antoviaque <xavier@antoviaque.org>
//
//  This software's license gives you freedom; you can copy, convey,
//  propagate, redistribute and/or modify this program under the terms of
//  the GNU Affero General Public License (AGPL) as published by the Free
//  Software Foundation (FSF), either version 3 of the License, or (at your
//  option) any later version of the AGPL published by the FSF.
//
//  This program is distributed in the hope that it will be useful, but
//  WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
//  General Public License for more details.
//
//  You should have received a copy of the GNU Affero General Public License
//  along with this program in a file in the toplevel directory called
//  "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
//

(function($) {

    $.cardstories_table = {

        name: 'table',

        poll: true,

        init: function(player_id, game_id, root) {
            // Table data storage
            this.init_table(root);
        },

        load_game: function(player_id, game_id, options, root) {
            // Table data storage
            this.init_table(root);
        },

        // Keep tables referenced by game_id on the root, to allow to store
        // table state between state() poll updates
        init_table: function(root) {
            // Keep track of games table information
            $(root).data('cardstories_table', {
                next_game_id: null,
                next_owner_id: null,
                on_next_owner_change_callback: null
            });
        },

        // Fetches table state for game game_id from the server.
        // If game_id is undefined, the server returns state for an
        // available table that the player can join.
        // Invokes callback with the table state as returned from the server.
        fetch_table_state: function(player_id, game_id, root, callback) {
            var query = {
                action: 'state',
                type: 'table',
                modified: 0,
                game_id: game_id,
                player_id: player_id
            };

            var success = function(data, status) {
                if ('error' in data) {
                    $.cardstories.panic(data.error);
                } else {
                    // data = [table_state, players_info],
                    // we don't care about players_info here.
                    callback(data[0]);
                }
            };

            $.cardstories.ajax({
                url: $.cardstories.url + '?' + $.param(query, true),
                success: success,
                async: false
            }, player_id, game_id, root);
        },

        // Invokes callback with an available game_id that the player can join.
        // If there are no available games, invokes callback with undefined.
        get_available_game: function(player_id, root, callback) {
            this.fetch_table_state(player_id, undefined, root, function(data) {
                callback(data.next_game_id);
            });
        },

        // Normally state() is called when a poll returns, but this allows
        // to get the state updated immediately (useful when polls aren't running)
        force_state_update: function(player_id, game_id, root) {
            var $this = this;
            $this.fetch_table_state(player_id, game_id, root, function(data) {
                $this.state(player_id, data, root);
            });
        },

        // Receives state data from the server
        // Store it for later use or proceed to next game if player is waiting for it
        state: function(player_id, data, root) {
            var game_id = data.game_id;
            var table = $(root).data('cardstories_table');
            var owner_changed = false;
            // Check if we need to warn about a owner change
            if (table.next_owner_id && table.next_owner_id !== data.next_owner_id) {
                owner_changed = true;
            }

            table.next_game_id = data.next_game_id;
            table.next_owner_id = data.next_owner_id;

            if (owner_changed && table.on_next_owner_change_callback) {
                table.on_next_owner_change_callback(data.next_owner_id);
            }

            this.check_next_game(player_id, game_id, root);
        },

        // Check if we are ready to redirect to the next game,
        // and invokes the callback with the next game id (might be undefined
        // if new game needs to be created) and options for $.cardstories.reload.
        check_next_game: function(player_id, game_id, root) {
            var table = $(root).data('cardstories_table');
            var callback = table.on_next_game_ready_callback;

            if (callback) {
                // Next game is ready to be joined
                if (table.next_game_id && table.next_game_id !== game_id) {
                    callback(table.next_game_id, {});
                    return true;
                }

                // It's the player's turn to create a game
                else if (player_id === table.next_owner_id) {
                    var options = {force_create: true};
                    if (game_id) {
                        options.previous_game_id = game_id;
                    }
                    callback(undefined, options);
                    return true;
                }
            }
            return false;
        },

        // Invoke the callback as soon as the game is created
        on_next_game_ready: function(player_id, game_id, root, callback) {
            var table = $(root).data('cardstories_table');
            table.on_next_game_ready_callback = callback;
            var is_ready = this.check_next_game(player_id, game_id, root, callback);

            return is_ready;
        },

        // Allows to register a callback, to be warned of next owner changes
        on_next_owner_change: function(player_id, game_id, root, callback) {
            var table = $(root).data('cardstories_table');
            table.on_next_owner_change_callback = callback;
        },

        // Returns the player_id of the player who should create the next game
        get_next_owner_id: function(game_id, root) {
            var table = $(root).data('cardstories_table');
            return table.next_owner_id;
        }
    };

    $.fn.cardstories_table = function(player_id, game_id) {
        $.cardstories_table.init(player_id, game_id, this);
        return this;
    };

    // Register cardstories plugin
    $.cardstories.register_plugin($.cardstories_table);

})(jQuery);
