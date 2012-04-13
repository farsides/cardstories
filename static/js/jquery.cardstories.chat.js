//
//     Copyright (C) 2011 Farsides <contact@farsides.com>
//
//     Authors:
//              Matjaz Gregoric <gremat@gmail.com>
//              Adolfo R. Brandes <arbrandes@gmail.com>
//              Xavier Antoviaque <xavier@antoviaque.org>
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

        poll: true,

        templates: {chat: '<div class="cardstories_chat_message"><strong>{player_id}:</strong> {sentence}</div>',
                    notification: '<div class="cardstories_chat_message"><a href="{href}"><strong>{player_id}</strong> created the game <strong>"{sentence}"</strong> <span class="cardstories_join_button">Join game</span></a></div>'},

        load_game: function(player_id, game_id, options, root) {
            var $this = this;
            var display = $('.cardstories_chat_display', root);
            var input = $('.cardstories_chat_input', root);

            // Save data for later use.
            $(root).data('cardstories_chat', {
                player_id: player_id,
                display: display,
                input: input,
                initialized_ts: new Date().getTime()
            });

            // Scroll chat div to bottom on window load event.
            // This is needed since exact element dimensions are not known yet
            // when the domready event fires in some browsers (Chrome for example).
            $(window).load(function() {
                $this.scroll_to_bottom(root);
            });

            // Initialize placeholder.
            input.placeholder();

            // Send message on enter, but only if there's at least one
            // character and we're not sending the placeholder itself.
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

        // Receives state data from the server. If there are messages, append
        // them to the display div.
        state: function(player_id, data, root) {
            var $this = this;
            if (data.messages) {
                var root_data = $(root).data('cardstories_chat');
                var play_pop = false;
                var play_ring = false;
                $.each(data.messages, function(_, message) {
                    var player_info = $.cardstories.get_player_info_by_id(message.player_id);
                    var tvars = {};
                    if (message.type == 'chat') {
                        tvars = {
                            player_id: player_info.name,
                            sentence: message.sentence
                        };
                        play_pop = true;
                    } else if (message.type === 'notification') {
                        var l = window.location;
                        var href = l.protocol + '//' + l.host + l.pathname;
                        href += $.cardstories.reload_link(message.game_id, {});
                        tvars = {
                            href: href,
                            player_id: player_info.name,
                            sentence: message.sentence
                        };
                        play_ring = true;
                    }
                    var div = $this.templates[message.type].supplant(tvars);
                    div = $(div);
                    div.find('a').unbind('click').click(function() {
                        $.cardstories.reload(player_id, message.game_id, {}, root);
                        return false;
                    });
                    root_data.display.append(div);
                });
                if (play_pop) {
                    $this.play_sound('pop', root);
                }
                if (play_ring) {
                    $this.play_sound('ring', root);
                }
                $this.scroll_to_bottom(root);
            }
        },

        // Scrolls the chat window to the bottom, so that the last received message
        // is in the viewport.
        scroll_to_bottom: function(root) {
            var display = $(root).data('cardstories_chat').display;
            display.scrollTop(display[0].scrollHeight);
        },

        // Plays a sound (depends on the audio plugin).
        play_sound: function(sound_id, root) {
            // Only play the sound for notifications that
            // happen at least 5 seconds after plugin initialization.
            // This is to prevent from flooding the player with rings
            // from old notifications on page refresh.
            var root_data = $(root).data('cardstories_chat');
            if (new Date().getTime() - root_data.initialized_ts > 5000) {
                $.cardstories_audio.play(sound_id, root);
            }
        }
    };

    $.fn.cardstories_chat = function(player_id) {
        return this;
    };

    // Register cardstories plugin.
    $.cardstories.register_plugin($.cardstories_chat);

})(jQuery);
