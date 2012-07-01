//
//     Copyright (C) 2011 Farsides <contact@farsides.com>
//
//     Authors:
//              Adolfo R. Brandes <arbrandes@gmail.com>
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

    $.cardstories_bot = {

        name: 'bot',

        poll: true,

        enable_join_input: '#cardstories_bot_enable_join',

        load_game: function(player_id, game_id, options, root) {
            var $this = this;
            var input = $(this.enable_join_input, root);

            // Send message on change
            input.change(function() {
                var enable_join = input.is(':checked');
                $this.send(enable_join, player_id, game_id, root);
            });
        },

        // Receives state data from the server.
        state: function(player_id, data, root) {
            var $this = this;
            var input = $(this.enable_join_input, root);
            if (data.enable_join && !input.is(':checked')) {
                input.prop('checked', true);
            } else if (!data.enable_join && input.is(':checked')) {
                input.prop('checked', false);
            }
        },

        // Sends message to the server.
        send: function(enable_join, player_id, game_id, root) {
            $.cardstories.send({
                action: 'bot',
                enable_join: enable_join,
                game_id: game_id
            }, null, player_id, game_id, root);
        }
    };

    $.fn.cardstories_bot = function(player_id) {
        return this;
    };

    // Register cardstories plugin.
    $.cardstories.register_plugin($.cardstories_bot);

})(jQuery);
