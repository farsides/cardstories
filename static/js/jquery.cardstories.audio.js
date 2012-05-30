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

    $.cardstories_audio = {

        name: 'audio',

        init: function(player_id, game_id, root) {
            var $root = $(root);

            // Don't initialize twice.
            if ($root.data('cardstories_audio')) {
                return;
            }

            soundManager.onready(function() {
                // Create SoundManager sound objects.
                var sounds = {};
                $.each($root.data('sounds'), function(i, sound) {
                    sound.autoLoad = true;
                    sounds[sound.id] = soundManager.createSound(sound);
                });

                // Save sound objects for later use.
                $root.data('cardstories_audio', {
                    sounds: sounds
                });
            });

            soundManager.ontimeout(function() {
                throw "cardstories_audio: Couldn't load SoundManager2 SWF files. No sound will be played.";
            });
        },

        // Stop any sound currently playing when loading a new game.
        // Useful when a player switches tabs while the levelup songs
        // are playing without closing the results box, for example.
        load_game: function(player_id, game_id, options, root) {
            this.stop_all();
        },

        play: function(sound_id, root) {
            var data = $(root).data('cardstories_audio');
            if (data && data.sounds && data.sounds[sound_id]) {
                data.sounds[sound_id].play();
            }
        },

        loop: function(sound_id, root, limit) {
            var data = $(root).data('cardstories_audio');
            if (data && data.sounds && data.sounds[sound_id]) {
                var i = 0;
                var loop = function(sound) {
                    if (!limit || ++i <= limit) {
                        sound.play({onfinish: function() {
                            loop(sound);
                        }});
                    }
                }
                loop(data.sounds[sound_id]);
            }
        },

        stop: function(sound_id, root) {
            var data = $(root).data('cardstories_audio');
            if (data && data.sounds && data.sounds[sound_id]) {
                data.sounds[sound_id].stop();
            }
        },

        // Stops all sounds currently playing.
        stop_all: function() {
            soundManager.stopAll();
        }
    };

    $.fn.cardstories_audio = function() {
        $.cardstories_audio.init(null, null, this);
        return this;
    };

    // Register cardstories plugin.
    $.cardstories.register_plugin($.cardstories_audio);

})(jQuery);
