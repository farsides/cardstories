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
            var $this = this;

            // Table data storage
            $this.init_game2table(game_id, root);

            // If game creation or a specific game aren't explicitly
            // requested, try to join an active table/game
            // TODO: This is disabled for now because it didn't play well with the
            //       new loading mechanism. It should be put directly into $.cardstories.bootstrap
            //       method instead.
            /*
            if(player_id && !$.query.get('create') && !game_id) {
                var table = $this.get_table_from_game_id(game_id, root);
                table.ready_for_next_game = true;
                $this.force_state_update(player_id, game_id, root);
            }
            */
        },

        load_game: function(player_id, game_id, options, root) {
            // Table data storage
            this.init_game2table(game_id, root);
        },

        // Keep tables referenced by game_id on the root, to allow to store
        // table state between state() poll updates
        init_game2table: function(game_id, root) {
            // Keep a unique reference for an undefined game_id,
            // to allow to include it in the game2table array
            if(!game_id) {
                game_id = 0;
            }

            // Keep track of games table information
            var game2table = {};
            game2table[game_id] = { next_game_id: null,
                                    next_owner_id: null,
                                    ready_for_next_game: false,
                                    reset_callback: null};
            $(root).data('cardstories_table', {game2table: game2table});
        },

        // Retreive table data
        get_table_from_game_id: function(game_id, root) {
            var game2table = $(root).data('cardstories_table').game2table;

            if(!game_id) {
                game_id = 0;
            }
            var table = game2table[game_id];

            return table;
        },

        // Normally state() is called when a poll returns, but this allows
        // to get the state updated immediately (useful when polls aren't running)
        force_state_update: function(player_id, game_id, root) {
            var $this = this;

            var query = {
                action: 'state',
                type: 'table',
                modified: 0,
                game_id: game_id,
                player_id: player_id,
            }

            var success = function(data, status) {
                if ('error' in data) {
                    $.cardstories.panic(data.error);
                } else {
                    // data = [table_state, players_info],
                    // we don't care about players_info here.
                    $this.state(player_id, data[0], root);
                }
            };

            $.cardstories.ajax({
                url: $.cardstories.url + '?' + $.param(query, true),
                success: success,
                async: false
            });
        },

        // Receives state data from the server
        // Store it for later use or proceed to next game if player is waiting for it
        state: function(player_id, data, root) {
            var $this = this;
            var game_id = data.game_id;
            var table = $this.get_table_from_game_id(game_id, root);
            var reset_needed = false;
            // Check if we need to warn about a owner change
            if(table.next_owner_id && table.next_owner_id !== data.next_owner_id) {
                reset_needed = true;
            }

            table.next_game_id = data.next_game_id;
            table.next_owner_id = data.next_owner_id;

            if(reset_needed && table.reset_callback) {
                table.reset_callback(data.next_owner_id);
            }

            $this.check_next_game(player_id, game_id, root);
        },

        // Check if we are ready to redirect to the next game
        // (and do it if we are)
        check_next_game: function(player_id, game_id, root) {
            var $this = this;
            var table = $this.get_table_from_game_id(game_id, root);
            if(table.ready_for_next_game) {
                // Next game is ready to be joined
                if(table.next_game_id && table.next_game_id !== game_id) {
                    $.cardstories.reload(player_id, table.next_game_id, {}, root);
                    return true;
                }

                // It's the player's turn to create a game
                else if(player_id === table.next_owner_id) {
                    var options = {force_create: true};
                    if(game_id) {
                        options.previous_game_id = game_id;
                    }
                    $.cardstories.reload(player_id, undefined, options, root);
                    return true;
                }
            }
            return false;
        },

        // Reload to the next game as soon it is created if ready_for_next_game is true
        load_next_game_when_ready: function(ready_for_next_game, player_id, game_id, root) {
            var $this = this;
            var table = $this.get_table_from_game_id(game_id, root);

            table.ready_for_next_game = ready_for_next_game;
            var is_ready = $this.check_next_game(player_id, game_id, root);

            return is_ready;
        },

        // Allows to register a callback, to be warned of next owner changes
        on_next_owner_change: function(player_id, game_id, root, reset_callback) {
            var $this = this;
            var table = $this.get_table_from_game_id(game_id, root);

            table.reset_callback = reset_callback;
        },

        // Returns the player_id of the player who should create the next game
        get_next_owner_id: function(player_id, game_id, root) {
            var $this = this;
            var table = $this.get_table_from_game_id(game_id, root);

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
