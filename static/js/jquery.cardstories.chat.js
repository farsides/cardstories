//
//     Copyright (C) 2011 Farsides <contact@farsides.com>
//
//     Authors:
//              Matjaz Gregoric <gremat@gmail.com>
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

    $.cardstories_chat = {

        name: 'chat',

        poll: 'chat',

        message_template: '<div class="cardstories_chat_message"><span>{player_id}:</span> {sentence}</div>',

        init: function(player_id, game_id, root) {

            // Don't initialize twice.
            if ($(root).data('cardstories_chat')) {
                return;
            }

            var display = $('.cardstories_chat_display', root);
            var input = $('.cardstories_chat_input', root);

            // Save data for later use.
            $(root).data('cardstories_chat', {
                player_id: player_id,
                display: display,
                input: input
            });

            // Initialize placeholder.
            input.placeholder();

            // Send message on enter, but only if there's at least one
            // character and we're not sending the placeholder itself.
            var $this = this;
            input.keydown(function(event) {
                if (event.which === 13) {
                    var sentence = input.val();
                    if ($.trim(sentence) && sentence !== input.attr('placeholder')) {
                        $this.send(player_id, sentence);
                    }
                    input.val('');
                }
            });
        },

        // Sends message to the server.
        send: function(player_id, sentence) {
            $.cardstories.send({
                action: 'message',
                player_id: player_id,
                sentence: sentence
            });
        },

        // Receives state data from the server.  If there are messages, append
        // them to the display div.
        state: function(player_id, data, root) {
            if (data.messages) {
                for (var i=0; i < data.messages.length; i++) {
                    var message = data.messages[i];
                    var sentence = message.sentence;
                    var player_id = message.player_id;
                    var div = this.message_template.supplant({player_id: player_id, sentence: sentence});
                    var display = $(root).data('cardstories_chat').display;
                    display.append(div).scrollTop(display[0].scrollHeight);
                }
            }
        }
    };

    $.fn.cardstories_chat = function(player_id, game_id) {
        $.cardstories_chat.init(player_id, game_id, this);
        return this;
    };

    // Register cardstories plugin.
    $.cardstories.register_plugin($.cardstories_chat);

})(jQuery);
