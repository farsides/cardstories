//
//  Copyright (C) 2011 Loic Dachary <loic@dachary.org>
//  Copyright (C) 2011-2012 Farsides <contact@farsides.com>
//
//  Authors:
//          Loic Dachary <loic@dachary.org>
//          Adolfo R. Brandes <arbrandes@gmail.com>
//          Matjaz Gregoric <mtyaka@gmail.com>
//          Xavier Antoviaque <xavier@antoviaque.org>
//          Rogério Hilbert Lima <rogerhil@gmail.com>
//          Chris McCormick <chris@mccormick.cx>
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

    $.cardstories = {
        url: "../resource",

        SEATS: 6,

        window: window,

        history: window.History,

        location: location,

        plugins: {},

        players_info: {},

        register_plugin: function(plugin) {
            this.plugins[plugin.name] = plugin;
        },

        noop: function() {},

        // Parses param 'name' out of the query string.
        // If param 'name' is an integer, calls parseInt on it before returning the result.
        // If param 'name' is not present in the query string, returns null.
        url_param: function(name) {
            var regex = new RegExp(name + '=([^&]*)');
            var query = this.location.search.substring(1);
            var match = regex.exec(query);
            var result = null;
            if (match) {
                result = decodeURIComponent(match[1].replace(/\+/g, ' '));
                if (/^\d+$/.test(result)) {
                    result = parseInt(result, 10);
                }
            }
            return result;
        },

        log: function(message) {
            var console = this.window.console;
            if (console && console.log) {
                console.log(message);
            }
        },

        panic: function(error, player_id, game_id, root) {
            var $this = this;
            var message = 'An unexpected error occured:\n';
            if (error.code && error.code === 'PANIC') {
                message += error.data;
            } else {
                message += JSON.stringify(error);
            }
            $this.log(error);
            $this.show_warning('.cardstories_panic', player_id, game_id, root, function() {
                $this.location.reload();
            });
        },

        show_warning: function(modal_selector, player_id, game_id, root, cb) {
            var $this = this;
            var element = $('.cardstories_notifications', root);
            this.set_active('notification', element, root);
            this.init_board_buttons(player_id, element, root);
            // Get the correct modal dialog.
            var modal = $(modal_selector, element);
            var overlay = $('.cardstories_modal_overlay', element);

            $('a', modal).unbind('click').click(function() {
                $this.close_modal(modal, overlay, function() {
                    if (cb) {
                        cb();
                    }
                });
            });

            this.poll_discard(root);
            if (player_id !== undefined) {
                this.poll_plugin(player_id, game_id, root);
            }
            this.display_modal(modal, overlay);
        },

        xhr_error: function(ajax_request, status, error, player_id, game_id, root) {
            var $this = this;
            $this.log('XHR ERROR: ' + status + ' ' + error);

            if (error) {
                // "abort" type errors aren't real errors, since they are caused
                // by aborting the ajax request inside poll_discard, so just ignore them.
                if (error !== 'abort') {
                    $this.panic(error, player_id, game_id, root);
                }
            } else {
                // Retry after 1 second.
                $this.setTimeout(function() {
                    $this.ajax(ajax_request, player_id, game_id, root);
                }, 1000);
            }
        },

        setTimeout: function(cb, delay) {
            return $.cardstories.window.setTimeout(cb, delay);
        },

        animationTimeout: function(cb, delay) {
            if (this.animations_off()) { delay = 0; }
            return this.setTimeout(cb, delay);
        },

        delay: function(root, delay, q) {
            if (this.animations_off()) { delay = 0; }
            return $(root).delay(delay, q);
        },

        animations_off: function() {
            return this.url_param('animations') === 'off';
        },

        ajax: function(options, player_id, game_id, root) {
            var $this = this;
            var request;
            var defaults = {
                async: true,
                cache: false,
                dataType: 'json',
                error: function(xhr, status, error) {
                    // Pass the ajax request to the error handler in
                    // order to be able to retry it.
                    $this.xhr_error(request, status, error, player_id, game_id, root);
                },
                global: false,
                timeout: 30000,
                type: 'GET'
            };
            request = $.extend(defaults, options);
            return jQuery.ajax(request);
        },

        // Event handler for History.js' statechange event, which is basically the same
        // as HTML5 popstate event. It is fired when calling history.pushState(), or when
        // the user clicks the back/forward buttons.
        onstatechange: function(root) {
            var deferred;
            var data = this.history.getState().data;
            if (data.player_id !== undefined) {
                root = $(root);
                // Discard any running poll.
                this.poll_discard(root);
                // Clear all queues.
                this.clear_queues(root);
                // Wipe out the DOM structure and re-create it from a clean copy.
                var dom_clone = root.data('dom_clone');
                root.empty();
                root.append(dom_clone);
                // Re-init cardstories.
                deferred = this.load_game(data.player_id, data.game_id, data.options, root);
                // Re-init Facebook SDK with the new DOM.
                FB.XFBML.parse();
            } else {
                deferred = $.Deferred().resolve();
            }

            return deferred;
        },

        // Loads another game without reloading the browser.
        reload: function(player_id, game_id, options, root) {
            var reload_link = this.reload_link(game_id, options);
            var data = {player_id: player_id, game_id: game_id, options: options};
            // Will fire the 'statechange' event, which will be handled by our 'onstatechange'
            // handler above, which will load the game.
            this.history.pushState(data, null, reload_link);
        },

        reload_link: function(game_id, options) {
            var params = {};

            // Default options
            var default_options = {
                force_create: false,
                previous_game_id: undefined,
                anonymous: false
            };

            options = $.extend(default_options, options);

            // game_id
            if (game_id) {
                params.game_id = game_id;
            }

            // player_id - Only add the player_id to the URL if it already is there (ie when
            // it has been filled manually by the player)
            var player_id = $.cardstories.url_param('player_id');
            if (player_id) {
                params.player_id = player_id;
            }

            // force_create - Allows to explicitely request the creation
            // of a new game, rather than letting the game chose a game to join
            if (options.force_create) {
                params.create = 1;
            }

            // anonymous - allows players who aren't participating in the game
            // (ie. because it is full) to observe the game in create/invitation state.
            if (options.anonymous) {
                params.anonymous = 1;
            }

            // previous_game_id - Allow to link a game being created to a previous game
            if (options.previous_game_id) {
                params.previous_game_id = options.previous_game_id;
            }

            // Add animations param, but only if already present.
            var animations = $.cardstories.url_param('animations');
            if (animations) {
                params.animations = animations;
            }

            var search = '';
            var encoded_params = $.param(params);
            if (encoded_params) {
                search = '?' + encoded_params;
            }
            return search;
        },

        create_new_game: function(player_id, previous_game_id, root) {
            var $this = this;
            $this.poll_discard(root);
            var query = {
                action: 'create',
                owner_id: player_id
            };
            if (previous_game_id) {
                query.previous_game_id = previous_game_id;
            }
            var success = function(data) {
                if ('error' in data) {
                    $this.panic(data.error, player_id, undefined, root);
                } else {
                    $this.reload(player_id, data.game_id, {}, root);
                }
            };
            var ajax_options = {
                url: $this.url + '?' + $.param(query, true),
                type: 'POST',
                async: false,
                success: success
            };
            $this.ajax(ajax_options, player_id, undefined, root);
        },

        create: function(player_id, game, root) {
            var $this = this;
            var inhibit_poll = false;
            var deferred;

            if (game.owner) {
                if (game.winner_card) {
                    deferred = $this.create_write_sentence(player_id, game, root);
                } else {
                    deferred = $this.create_pick_card(player_id, game, root);
                }
            } else {
                if (game.self) {
                    deferred = $this.create_wait_for_story(player_id, game, root);
                } else if ($.cardstories.url_param('anonymous')) {
                    deferred = $this.create_wait_for_story(player_id, game, root);
                } else {
                    inhibit_poll = true;
                    $this.player_participate(player_id, game, root);
                }
            }

            if (!inhibit_poll) {
                $this.poll_discard(root);
                $this.poll({
                    type: ['game'],
                    game_id: game.id,
                    player_id: player_id
                }, player_id, game.id, root, function() {
                    $this.game(player_id, game.id, root);
                });
            }

            return deferred;
        },

        create_setup_next_owner_change_handler: function(player_id, game, element, root) {
            var $this = this;
            $.cardstories_table.on_next_owner_change(player_id, game.id, root, function(next_owner_id) {
                var modal = $('.cardstories_next_owner_change', element);
                var overlay = $('.cardstories_modal_overlay', element);

                // If this player is the next owner, notify him,
                // otherwise close the dialog if it is opened.
                if (player_id === next_owner_id) {
                    var player_name = $('.cardstories_player_name', modal);

                    player_name.html($this.get_player_info_by_id(next_owner_id).name);
                    $this.display_modal(modal, overlay, null, function() {
                        $this.poll_discard(root);
                        $this.reload(player_id, undefined, {force_create: true, previous_game_id: game.id}, root);
                    });
                } else if (modal.css('display') !== 'none') {
                    $this.close_modal(modal, overlay);
                }
            });
        },

        create_setup_next_game_ready_handler: function(player_id, game, element, root) {
            var $this = this;
            $.cardstories_table.on_next_game_ready(player_id, game.id, root, function(next_game_id, next_game_opts) {
                var next_owner_id = $.cardstories_table.get_next_owner_id(game.id, root);

                // If this is the player who created the next game, then there's no
                // point in showing him the message as he must be well aware of the fact.
                if (player_id !== next_owner_id) {
                    var modal = $('.cardstories_next_game_ready', element);
                    var overlay = $('.cardstories_modal_overlay', element);
                    var player_name = $('.cardstories_player_name', modal);

                    player_name.html($this.get_player_info_by_id(next_owner_id).name);
                    $this.display_modal(modal, overlay, null, function() {
                        $this.poll_discard(root);
                        $this.reload(player_id, next_game_id, next_game_opts, root);
                    });
                }
            });
        },

        create_wait_for_story: function(player_id, game, root) {
            var element = $('.cardstories_invitation .cardstories_pick', root);
            this.set_active('invitation_pick', element, root, game);
            this.display_progress_bar('player', 1, element, root);
            this.display_master_info(this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);

            if (game.self) {
                this.create_setup_next_owner_change_handler(player_id, game, element, root);
                this.create_setup_next_game_ready_handler(player_id, game, element, root);
            }

            this.create_invitation_display_board(player_id, game, element, root, false);

            var deferred = $.Deferred();
            this.replay_create_game(game, element, root, function() {
                deferred.resolve();
            });
            return deferred;
        },

        animate_progress_bar: function(step, element, cb) {
            var progress = $('.cardstories_progress', element);
            var mark = $('.cardstories_progress_mark', progress);

            // Advance step data, but save current.
            var cur = progress.data('step');
            progress.data('step', step);

            // Append the next mark temporarily to the progress bar so we can
            // grab it's left position, then remove it.
            var tmp_mark = $('<div>')
                            .addClass('cardstories_progress_mark')
                            .addClass('cardstories_progress_mark_' + step)
                            .appendTo(progress);
            var final_left = tmp_mark.position().left;
            tmp_mark.remove();

            // Animate the mark.
            // I fail to understand why, but tmp_mark and final_left are sometimes
            // undefined during test runs, which wracks havoc on IE8.
            if (typeof final_left !== 'undefined') {
                mark.animate({left: final_left}, 500, function() {
                    mark.removeClass('cardstories_progress_mark_' + cur);
                    mark.addClass('cardstories_progress_mark_' + step);
                    $('.cardstories_progress .cardstories_step_' + step, element).addClass('selected');
                    for (var i=cur; i < step; i++) {
                        $('.cardstories_progress .cardstories_step_' + i, element)
                            .removeClass('selected')
                            .addClass('old');
                    }
                    if (cb) {
                        cb();
                    }
                });
            } else if (cb) {
                cb();
            }
        },

        // For best results with animate_scale, the element must be positioned
        // absolutely, and its children must be sized and positioned relatively
        // (i.e., "em" instead of "px", percentages for widths and heights).
        animate_scale: function(reverse, factor, duration, el, cb) {
            // Show self and all parents first, so that the measurements
            // give correct results.
            el.parents().andSelf().show();
            var big_top = el.position().top;
            var big_left = el.position().left;
            var big_width = el.width();
            var big_height = el.height();
            var big_fontsize = parseInt(el.css('font-size'), 10);

            var small_width = Math.floor(big_width / factor);
            var small_height = Math.floor(big_height / factor);
            var small_top = big_top + Math.floor((big_height - small_height)/2);
            var small_left = big_left + Math.floor((big_width - small_width)/2);
            var small_fontsize = Math.floor(big_fontsize / factor);

            if (!reverse) {
                // Set the initial small size.
                el.css({
                    top: small_top,
                    left: small_left,
                    width: small_width,
                    height: small_height,
                    fontSize: small_fontsize
                });

                // Animate.
                el.animate({
                    top: big_top,
                    left: big_left,
                    width: big_width,
                    height: big_height,
                    fontSize: big_fontsize
                }, duration, function() {
                    if (cb) {
                        cb();
                    }
                });
            } else {
                // Animate and the hide the element.
                el.animate({
                    top: small_top,
                    left: small_left,
                    width: small_width,
                    height: small_height,
                    fontSize: small_fontsize
                }, duration, function() {
                    el.hide();
                    // Reset to original size.
                    el.css({
                        top: big_top,
                        left: big_left,
                        width: big_width,
                        height: big_height,
                        fontSize: big_fontsize
                    });

                    if (cb) {
                        cb();
                    }
                });
            }
        },

        animate_sprite: function(movie, fps, frames, rewind, loop, cb) {
            if (this.animations_off()) {
                  // Show the last frame immediately.
                movie.show().sprite({
                    fps: fps,
                    rewind: !rewind,
                    no_of_frames: frames,
                    play_frames: 1,
                    oncomplete: cb
                });
            } else {
                movie.show().sprite({
                    fps: fps,
                    no_of_frames: frames,
                    play_frames: loop ? null : frames,
                    rewind: rewind,
                    oncomplete: cb
                });
            }
        },

        clear_queues: function(root) {
            var queues = $(root).data('queues');
            if (queues) {
                for (var i = 0; i < queues.length; i++) {
                    $(root).clearQueue(queues[i]);
                }
            }
            $(root).data('queues', []);
        },

        create_queue: function(root) {
            if ($(root).data('queues') == undefined) {
                $(root).data('queues', []);
            }
            var len = $(root).data('queues').length;
            var queue = 'q' + len;
            $(root).data('queues').push(queue);

            return queue;
        },

        create_pick_card: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_create .cardstories_pick_card', root);
            this.set_active('create_pick_card', element, root, game);
            this.display_progress_bar('owner', 1, element, root);
            this.display_master_info($this.get_player_info_by_id(player_id), element);
            this.init_board_buttons(player_id, element, root);
            this.create_setup_next_game_ready_handler(player_id, game, element, root);
            var cards = $.map(game.self[2], function(card, index) {
                return {'value': card};
            });

            var deferred = $.Deferred();
            var q = $this.create_queue(root);

            $this.create_owner_join_helper(player_id, game, element, root);

            var card_value, card_index;
            // Only run the deal animations once.
            if (!element.hasClass('cardstories_noop')) {
                element.addClass('cardstories_noop');
                // Deal the cards
                $(root).queue(q, function(next) {
                    $this.create_pick_card_animate(cards, element, root, next);
                });

                // Set up the dock for card selection, and show the modal box. The
                // user won't be able to select a card until "OK" is clicked.
                $(root).queue(q, function(next) {
                    var ok = function(_card_value, _card_index) {
                        // Stop the poll for the rest of the animation.
                        $this.poll_discard(root);
                        // The selected card will be needed later in the queue.
                        card_value = _card_value;
                        card_index = _card_index;
                        var query = {
                            action: 'set_card',
                            player_id: player_id,
                            game_id: game.id,
                            card: card_value
                        };
                        var callback = function() {
                            $this.create_pick_card_to_write_sentence(player_id, game, element, card_index, card_value, root);
                        };
                        $this.send(query, callback, player_id, game.id, root);
                    };

                    $this.select_cards('create_pick_card', cards, ok, element, root).done(function() {
                        // Hide the cards in the back.
                        $('.cardstories_deck .cardstories_card', element).hide();

                        // Delay the appearance of the modal box artificially, since
                        // jqDock doesn't provide a hook for when expansion finishes.
                        $this.animationTimeout(function() {
                            var modal = $('.cardstories_info', element);
                            var overlay = $('.cardstories_modal_overlay', element);
                            $this.display_modal(modal, overlay, function() {
                                deferred.resolve();
                            });
                        }, 250);
                    });
                });
            } else {
                deferred.resolve();
            }

            $(root).dequeue(q);

            return deferred;
        },

        create_pick_card_to_write_sentence: function(player_id, game, element, card_index, card_value, root) {
            var $this = this;
            var q = $this.create_queue(root);

            $(root).queue(q, function(next) {
                $this.create_pick_card_animate_fly_to_deck(card_index, element, root, next);
            });
            $(root).queue(q, function(next) {
                $this.animate_center_picked_card(element, card_index, card_value, next);
            });
            $(root).queue(q, function(next) {
                $this.animate_progress_bar(2, element, next);
            });

            // Finally, initialize the next state.
            $(root).queue(q, function(next) {
                $this.game(player_id, game.id, root);
            });

            $(root).dequeue(q);
        },

        existing_players_show_helper: function(existing_players, game, element, root) {
            var $this = this;
            var players = game.players;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_player_seat', snippets);
            var slotno = 0;
            $.each(players, function(i, player) {
                // Skip the owner.
                if (player.id !== game.owner_id) {
                    slotno++;

                    var is_new = $.grep(existing_players, function(p) {
                        return p.id === player.id;
                    }).length === 0;

                    if (!is_new) {
                        // Set up the player seat.
                        var slot = $('.cardstories_player_seat.cardstories_player_seat_' + slotno, element);
                        if (!slot.hasClass('cardstories_noop_join')) {
                            slot.addClass('cardstories_noop_join');
                            slot_snippet.clone().children().appendTo(slot);
                            slot.addClass('cardstories_player_seat_joined');
                            var player_info = $this.get_player_info_by_id(player.id);
                            $this.display_player_info(player_info, slot);
                            $('.cardstories_player_invite.cardstories_player_seat_' + slotno, element).hide();
                            $('.cardstories_player_status', slot).html('joined the game!');
                            slot.show();
                        }
                    }
                }
            });
        },

        create_owner_join_helper: function(player_id, game, element, root, cb) {
            var $this = this;
            var players = game.players;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_player_seat', snippets);
            var last = players.length - 1;
            var q = $this.create_queue(root);

            var delay_next = false;
            var play_sound = true;
            var slotno = 0;
            $.each(players, function(i, player) {
                // Delay this player, but only if there was at least one change
                // displayed for the previous ones.
                if (delay_next) {
                    $this.delay(root, 350, q);
                    delay_next = false;
                }

                // Skip the owner.
                if (player.id !== game.owner_id) {
                    slotno++;

                    // Set up the player seat.
                    var slot = $('.cardstories_player_seat.cardstories_player_seat_' + slotno, element);
                    if (!slot.hasClass('cardstories_noop_join')) {
                        $(root).queue(q, function(next) {
                            slot.addClass('cardstories_noop_join');
                            delay_next = true;
                            slot_snippet.clone().children().appendTo(slot);
                            slot.addClass('cardstories_player_seat_joined');
                            $('.cardstories_player_status', slot).html('joined the game!');
                            var player_info = $this.get_player_info_by_id(player.id);
                            $this.display_player_info(player_info, slot);
                            // Play a sound, but only once per each batch of players.
                            if (play_sound) {
                                $.cardstories_audio.play('join', root);
                                play_sound = false;
                            }
                            slot.fadeIn(function() {
                                $(this).show(); // A workaround for http://bugs.jquery.com/ticket/8892
                                next();
                            });
                        });
                    }
                }

                if (i === last && cb) {
                    $(root).queue(q, function(next) {
                        cb();
                        next();
                    });
                }
            });

            $(root).dequeue(q);
        },

        animate_center_picked_card: function(element, index, card, callback) {
            var dock = $('.cardstories_cards_hand .cardstories_cards', element);
            var card_element = $('.cardstories_card', dock).eq(index);
            var card_selected = $('.cardstories_card_foreground', card_element);

            // Image size & position varies according to the state of jqDock when it was frozen)
            // The dock element is contained in multiple <div> - left position is the sum of all elements
            var initial_left = card_element.parents('div[class^="jqDockMouse"]').position().left;
            initial_left += card_element.parents('.jqDock').position().left;
            initial_left += dock.position().left;
            // Top position of the card: top position of the bottom of the dock minus card height
            var dock_bottom_pos = dock.position().top + dock.height();
            var initial_top = dock_bottom_pos - card_element.height();

            // Replace the docked card by an absolutely positioned image, to be able to move it
            var card_flyover = $('.cardstories_card_flyover', element);
            var meta = card_flyover.metadata({type: 'attr', name: 'data'});
            var src = meta.card.supplant({card: card});

            $('.cardstories_card_foreground', card_flyover).attr('src', src);
            card_flyover.css({
                top: initial_top,
                left: initial_left,
                width: card_selected.width(),
                height: card_selected.height(),
                display: 'block'
            });
            dock.css({'display': 'none'});

            // Center the card
            card_flyover.animate({
                    top: dock_bottom_pos - meta.final_height,
                    left: meta.final_left,
                    height: meta.final_height,
                    width: meta.final_width
                }, 500, function() {
                    callback();
            });
        },

        create_pick_card_animate: function(card_specs, element, root, cb) {
            var $this = this;
            var cards = $('.cardstories_deck .cardstories_card', element);

            $this.create_pick_card_animate_fly_to_board(cards, element, root, function() {
                $this.create_pick_card_animate_morph_into_jqdock(cards, card_specs, element, root, cb);
            });
        },

        create_pick_card_animate_fly_to_board: function(cards, element, root, cb) {
            var $this = this;
            var nr_of_cards = cards.length;
            var card_fly_velocity = 1.2;   // in pixels per milisecond
            var card_delay = 100;   // delay in ms after each subsequent card starts "flying" from the deck
            var vertical_offset = 8;
            var vertical_rise_duration = 300;
            var q = $this.create_queue(root);

            cards.each(function(i) {
                var card = $(this);
                var meta = card.metadata({type: 'attr', name: 'data'});
                var starting_top = card.position().top;
                var starting_left = card.position().left;
                var final_top = meta.final_top;
                var final_left = meta.final_left;
                var keyframe_top = final_top + vertical_offset;

                var fly_length = Math.sqrt(Math.pow(keyframe_top - starting_top, 2) + Math.pow(final_left - starting_left, 2));
                var fly_duration = fly_length / card_fly_velocity;

                // The first card should start flying immediately,
                // but each subsequent card should be delayed.
                if (i !== 0) {
                    $this.delay(root, card_delay, q);
                }

                // The callback passed to this function should be fired
                // after the last card raises to its final position.
                var callback = (i === nr_of_cards - 1) ? cb : null;

                $(root).queue(q, function(next) {
                    card.animate({top: keyframe_top, left: final_left}, fly_duration, function() {
                        card.animate({top: final_top}, vertical_rise_duration, callback);
                    });
                    next();
                });
            });

            $(root).dequeue(q);
        },

        create_pick_card_animate_morph_into_jqdock: function(cards, card_specs, element, root, cb) {
            var $this = this;
            var nr_of_cards = cards.length;
            var card_width = cards.width();
            var src_template = $('.cardstories_card_template', element).metadata({type: 'attr', name: 'data'}).card;
            var turnaround_duration = 600;
            var q = $this.create_queue(root);

            $(root).queue(q, function(next) {
                cards.each(function(i) {
                    var card = $(this);
                    var spec = card_specs[nr_of_cards - i - 1];
                    var meta = card.metadata({type: 'attr', name: 'data'});
                    card.animate({width: 0, left: meta.final_left + card_width/2}, turnaround_duration/2, function() {
                        var foreground_src = src_template.supplant({card: spec.value});
                        // Elsewhere in the code, one card usually consists of two images stacked one
                        // on top of another: the foregrond and the background image, where the
                        // background is visible as the border.
                        // Here we only have one (the foreground) image, so we need to emulate a border with CSS.
                        // While it would be more consistent to also use two images here, jqDock only expects
                        // one image, and the pain of working around this jqDock limitation wouldn't be worth it, IMHO.
                        card.attr('src', foreground_src).addClass('cardstories_card_border');
                        if (i === nr_of_cards - 1) {
                            next();
                        }
                    });
                });
            });

            $(root).queue(q, function(next) {
                cards.each(function(i) {
                    var card = $(this);
                    var meta = card.metadata({type: 'attr', name: 'data'});
                    card.animate({width: card_width, left: meta.final_left}, turnaround_duration/2, function() {
                        if (i === nr_of_cards - 1) {
                            next();
                        }
                    });
                });
            });

            $(root).queue(q, function(next) {
                cb();
                next();
            });

            $(root).dequeue(q);
        },

        create_pick_card_animate_fly_to_deck: function(card_index, element, root, cb) {
            var $this = this;
            var deck = $('.cardstories_deck', element);
            var cards = $('.cardstories_card', deck);
            var docked_cards = $('.cardstories_cards_hand .cardstories_card', element);
            var nr_of_cards = cards.length;
            var card_fly_velocity = 1.2;   // in pixels per milisecond
            var card_delay = 100;   // delay in ms after each subsequent card starts "flying" back to the deck
            var deck_cover = $('.cardstories_deck_cover', deck);
            deck_cover.show();
            var final_top = deck_cover.position().top;
            var final_left = deck_cover.position().left;
            var final_width = deck_cover.width();
            var final_height = deck_cover.height();
            deck_cover.hide();
            var deck_offset = deck.offset();
            var q = $this.create_queue(root);

            cards.each(function(i) {
                var card = $(this).show();
                var rindex = nr_of_cards - i - 1;
                // Hide the chosen card (we will use the one handled by jqDock)
                // and move on to the next one.
                if (rindex === card_index) {
                    card.hide();
                    return;
                }

                var docked_card = docked_cards.find('.cardstories_card_foreground').eq(rindex);
                var height = docked_card.height();
                var width = docked_card.width();
                var starting_left = docked_card.offset().left - deck_offset.left;
                var starting_top = card.position().top - height + final_height;
                var fly_length = Math.sqrt(Math.pow(starting_top - final_top, 2) + Math.pow(starting_left - final_left, 2));
                var fly_duration = fly_length / card_fly_velocity;

                card.css({top: starting_top, left: starting_left, height: height, width: width});

                // The first card should start flying immediately,
                // but each subsequent card should be delayed.
                if (i !== 0) {
                    $this.delay(root, card_delay, q);
                }

                $(root).queue(q, function(next) {
                    var final_props = {
                        top: final_top,
                        left: final_left,
                        width: final_width,
                        height: final_height
                    };
                    card.animate(final_props, fly_duration, function() {
                        // hide the card so that non-rounded borders aren't too obvious in IE8.
                        card.hide();
                        // The callback function should be called after the last card
                        // reaches its final position.
                        if (rindex === (card_index === 0 ? 1 : 0)) {
                            cb();
                        }
                    });
                    next();
                });
            });

            docked_cards.filter(':not(.cardstories_card_selected)').hide();
            $(root).dequeue(q);
        },

        create_write_sentence_animate_start: function(card, element, root, cb) {
            var $this = this;
            var write_box = $('.cardstories_write', element);
            var card_shadow = $('.cardstories_card_shadow', element);
            var card_template = $('.cardstories_card_template', element);
            var card_imgs = $('img', card_template);
            var card_foreground = card_imgs.filter('.cardstories_card_foreground');
            var card_flyover = $('.cardstories_pick_card .cardstories_card_flyover', root);

            // Set the card's src attribute first.
            var src = card_template.metadata({type: 'attr', name: 'data'}).card.supplant({card: card});
            card_foreground.attr('src', src);

            var final_top = card_template.position().top;
            var final_left = card_template.position().left;
            var final_width = card_imgs.width();
            var final_height = card_imgs.height();
            var starting_width = card_flyover.metadata({type: 'attr', name: 'data'}).final_width;
            var ratio = final_width / starting_width;
            var starting_height = Math.ceil(final_height / ratio);
            var animation_duration = 500;

            // Set the card into its initial state. The css values will need to
            // be adjusted properly once the layouts are finished.
            write_box.hide();
            card_shadow.hide();
            card_template.css({
                top: final_top + final_height - starting_height,
                left: final_left + ((final_width - starting_width) / 2)
            });
            card_imgs.css({
                width: starting_width,
                height: starting_height
            });

            // If defined, run the callback (used in the tests).
            if (cb) { cb('before_animation'); }

            // Animate towards the final state.
            var q = $this.create_queue(root);
            $(root).queue(q, function(next) {
                card_template.animate({
                    top: final_top,
                    left: final_left
                }, animation_duration);
                card_imgs.animate({
                    width: final_width,
                    height: final_height
                }, animation_duration, next);
            });
            $(root).queue(q, function(next) {
                card_shadow.fadeIn('fast');
                write_box.fadeIn('fast', function() {
                    $(this).show(); // A workaround for http://bugs.jquery.com/ticket/8892
                    next();
                });
            });
            // If set, run the callback at the end of the queue.
            if (cb) {
                $(root).queue(q, function(next) {cb('after_animation');});
            }
            $(root).dequeue(q);
        },

        create_write_sentence_animate_end: function(card, element, root, cb) {
            var $this = this;
            var card_template = $('.cardstories_card_template', element);
            var card_img = $('img', card_template);
            var card_shadow = $('.cardstories_card_shadow', element);
            var final_container = $('.cardstories_invitation', root);
            var final_element = $('.cardstories_owner', final_container);
            var final_card_template = $('.cardstories_picked_card', final_element);
            var write_box = $('.cardstories_write', element);
            var sentence_box = $('.cardstories_sentence_box', element);
            var final_sentence_box = $('.cardstories_sentence_box', final_element);

            // Calculate final position and dimensions.
            // Temporarily show destination elements by adding the cardstories_active class.
            // Using jQuery's show/hide doesn't work here, because it leaves the elements
            // with inline styles set to display:none and therefore invisible.
            final_container.addClass('cardstories_active');
            final_element.addClass('cardstories_active');
            var card_top = final_card_template.position().top;
            var card_left = final_card_template.position().left;
            var card_width = final_card_template.width();
            var card_height = final_card_template.height();
            var sentence_top = final_sentence_box.position().top;
            var sentence_left = final_sentence_box.position().left;
            var sentence_width = final_sentence_box.width();
            var sentence_height = final_sentence_box.height();
            final_element.removeClass('cardstories_active');
            final_container.removeClass('cardstories_active');

            // Animate!
            var text = $('.cardstories_sentence', write_box).val();
            $('.cardstories_sentence', sentence_box).text(text);
            var q = $this.create_queue(root);
            $(root).queue(q, function(next) {
                write_box.fadeOut('fast');
                sentence_box.fadeIn('fast', function() {
                    $(this).show(); // A workaround for http://bugs.jquery.com/ticket/8892
                    next();
                });
            });
            $(root).queue(q, function(next) {
                write_box.hide();
                sentence_box.animate({
                    top: sentence_box.position().top + 20,
                    left: sentence_box.position().left + 30,
                    width: sentence_width,
                    height: sentence_height
                }, 200, next);
            });
            $(root).queue(q, function(next) {
                card_shadow.hide();
                var duration = 500;
                card_template.animate({
                    top: card_top,
                    left: card_left
                }, duration);
                card_img.animate({
                    width: card_width,
                    height: card_height
                }, duration);
                sentence_box.animate({
                    top: sentence_top,
                    left: sentence_left
                }, duration, next);
            });
            // If set, run the callback at the end of the queue.
            if (cb) {
                $(root).queue(q, function(next) {cb();});
            }
            $(root).dequeue(q);
        },

        create_write_sentence: function(player_id, game, root) {
            var $this = this;
            var state = $(root).data('cardstories_state');
            var existing_players = state && state.game && state.game.players || [];
            var element = $('.cardstories_create .cardstories_write_sentence', root);
            var card = game.winner_card;
            this.set_active('create_write_sentence', element, root, game);
            this.display_progress_bar('owner', 2, element, root);
            this.display_master_info($this.get_player_info_by_id(player_id), element);
            this.init_board_buttons(player_id, element, root);
            this.create_setup_next_game_ready_handler(player_id, game, element, root);
            $('.cardstories_card', element).attr('class', 'cardstories_card cardstories_card' + card + ' {card:' + card + '}');


            // Immediately display seats for players who have already joined the game previously.
            this.existing_players_show_helper(existing_players, game, element, root);
            // Show players that are new this time (with animation and sound).
            this.create_owner_join_helper(player_id, game, element, root);

            if (!element.hasClass('cardstories_noop')) {
                element.addClass('cardstories_noop');
                this.create_write_sentence_animate_start(card, element, root);

                var text = $('textarea.cardstories_sentence', element);
                var input = $('.cardstories_submit', element).hide();

                // Show number of characters remaining
                text.limit('80','#cardstories_char_left_counter');

                var is_sentence_valid = function() {
                    var trimmedText = $.trim(text.val());
                    var placeholderValue = $.data(text[0], 'placeholderValue');
                    return trimmedText.length > 1 && trimmedText !== placeholderValue;
                };

                text.bind('keyup click change', function() {
                    if (is_sentence_valid()) {
                        input.show();
                    } else {
                        input.hide();
                    }
                });

                var submit = function() {
                    if (!is_sentence_valid()) {
                        return false;
                    }

                    $this.create_write_sentence_animate_end(card, element, root, function() {
                        $this.animate_progress_bar(3, element, function() {
                            // Discard any polls, otherwise sometimes there are double
                            // 'new game' notifications in the chat.
                            $this.poll_discard(root);

                            var success = function(data, status) {
                                if ('error' in data) {
                                    $this.panic(data.error, player_id, game.id, root);
                                } else {
                                    $this.game(player_id, game.id, root, {async: false});
                                }
                            };
                            var query = {
                                action: 'set_sentence',
                                game_id: game.id,
                                player_id: player_id
                            };
                            var sentence = encodeURIComponent($('.cardstories_sentence', element).val());
                            $this.ajax({
                                url: $this.url + '?' + $.param(query, true),
                                type: 'POST',
                                async: false,
                                data: 'sentence=' + sentence,
                                success: success
                            }, player_id, game.id, root);
                        });
                    });
                    return true;
                };
                text.val('').placeholder({ onSubmit: submit });
            }
        },

        advertise: function(owner_id, game_id, element, root) {
            var $this = this;
            var box = $('.cardstories_advertise', element);
            var overlay = $('.cardstories_owner .cardstories_modal_overlay', root);
            if (box.is(':visible')) {
                return;
            }

            // Set game copy URL
            var input = $('input.cardstories_copy_url', element)
            var url = $this.location.protocol + '//' + $this.location.host + '/?game_id=' + game_id;
            input.val(url);

            // Select all when clicked.
            input.unbind('click').click(function() {
                $(this).select();
            });

            // Show FB only after zooming in.
            var fb = $('.fb-like', box).hide();
            this.display_modal(box, overlay, function() {
                fb.show();
            });
        },

        poll_timeout: 30 * 1000, // must be identical to the --poll-timeout value
                                 // server side

        add_plugin_polls: function(request, root) {
            $.each(this.plugins, function(i) {
                if (this.poll && $.inArray(this.name, request.type) === -1 ) {
                    request.type.push(this.name);
                }
            });
            return request;
        },

        poll: function(request, player_id, game_id, root, cb) {
            var $this = this;

            request.action = 'poll';

            // Only allow one poll at a time, and don't allow polling if
            // polling is undefined.
            if ($(root).data('polling') !== false) {
                this.poll_ignore(request);
                return false;
            }

            // Init type if not set (used in polls initiated for the benefit of
            // plugins).
            if (!request.type) {
                request.type = [];
            }

            // Add plugin polls.
            request = this.add_plugin_polls(request, root);

            // Bail out if no poll types are set.
            if (!request.type.length) {
                return false;
            }

            $(root).data('polling', true);
            var success = function(answer, status) {
                $(root).data('polling', false);
                if ('error' in answer) {
                    $this.panic(answer.error, player_id, game_id, root);
                } else {
                    if ('timeout' in answer) {
                        $this.poll(request, player_id, game_id, root, cb);
                    } else if (cb) {
                        cb();
                    }
                }
            };

            request.modified = $(root).data('cardstories_modified');

            var poll = $this.ajax({
                timeout: $this.poll_timeout * 2,
                url: $this.url + '?' + $.param(request, true),
                success: success
            }, player_id, game_id, root);

            // Save poll for discarding, when necessary.
            $(root).data('poll', poll);

            return true;
        },

        poll_ignore: function(request) {},

        poll_discard: function(root) {
            if ($(root).data('polling') === true) {
                $(root).data('polling', false);
                $(root).data('poll').abort();
            }
        },

        poll_plugin: function(player_id, game_id, root, callback) {
            var $this = this;

            // Available plugin states.
            var type = [];
            $.each(this.plugins, function(i) {
                if (this.poll) {type.push(this.name);}
            });

            // Only enter the loop if there are applicable plugin polls.
            if (type.length) {
                var success = function(data, status) {
                    if ('error' in data) {
                        $this.panic(data.error, player_id, game_id, root);
                    } else {
                        // Save greatest modification time.
                        var modified = 0;
                        for (var i=0; i < data.length; i++) {
                            if (data[i].modified && data[i].modified > modified) {
                                modified = data[i].modified;
                            }
                        }
                        if (modified && modified > 0) {
                            $(root).data('cardstories_modified', modified);
                        }

                        // Store players_info data first
                        $this.update_players_info(data, player_id, root);

                        // Call plugin states.
                        $.each(data, function(i) {
                            var datum = this;
                            var plugin = $this.plugins[datum.type];
                            if (plugin && plugin.state) {
                                $this.setTimeout(function() { plugin.state(player_id, datum, root); }, 30);
                            }
                        });

                        // Start a poll (the function will take care of including
                        // the plugin types).
                        $this.poll({
                            'player_id': player_id,
                            'game_id': game_id
                        }, player_id, game_id, root, function() {
                            $this.poll_plugin(player_id, game_id, root);
                        });

                    }

                    if (callback) {
                        callback();
                    }
                };

                var request = {
                    action: 'state',
                    type: type,
                    modified: $(root).data('cardstories_modified'),
                    player_id: player_id,
                    game_id: game_id
                };

                $this.ajax({
                    url: $this.url + '?' + $.param(request, true),
                    success: success
                }, player_id, game_id, root);
            } else if (callback) {
                callback();
            }
        },

        invitation: function(player_id, game, root) {
            var $this = this;
            var deferred;
            var inhibit_poll = false;
            if (game.owner) {
                deferred = this.invitation_owner(player_id, game, root);
            } else {
                if ($.cardstories.url_param('anonymous')) {
                    deferred = this.invitation_anonymous(player_id, game, root);
                } else {
                    if (game.self) {
                        if (game.self[0] === null) {
                            deferred = this.invitation_pick(player_id, game, root);
                        } else {
                            deferred = this.invitation_pick_wait(player_id, game, root);
                        }
                    } else {
                        inhibit_poll = true;
                        deferred = this.player_participate(player_id, game, root);
                    }
                }
            }

            if (!inhibit_poll) {
                $this.poll_discard(root);
                $this.poll({
                    'type': ['game'],
                    'game_id': game.id,
                    'player_id': player_id
                }, player_id, game.id, root, function() {
                    $this.game(player_id, game.id, root);
                });
            }

            return deferred;
        },

        invitation_owner: function(player_id, game, root) {
            var $this = this;
            var state = $(root).data('cardstories_state');
            var existing_players = state && state.game && state.game.players || [];
            var element = $('.cardstories_invitation .cardstories_owner', root);
            this.set_active('invitation_owner', element, root, game);
            this.display_progress_bar('owner', 3, element, root);
            this.display_master_info($this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);
            $('.cardstories_sentence', element).text(game.sentence);
            var picked_card = $('.cardstories_picked_card', element);
            var src = picked_card.metadata({type: 'attr', name: 'data'}).card.supplant({card: game.winner_card});
            picked_card.find('.cardstories_card_foreground').attr('src', src);
            var go_vote = $('.cardstories_go_vote', element);
            var advertise = $('.cardstories_advertise', element);
            var advertise_close = $('.cardstories_advertise_close', advertise);
            var advertise_next = $('.cardstories_advertise_next', advertise);

            // Immediately display seats for players who have already joined the game previously.
            this.existing_players_show_helper(existing_players, game, element, root);

            // Enable closing the advertise box after 2 players join.
            if (game.players.length > 2 && advertise_close.hasClass('cardstories_button_disabled')) {
                advertise_close.removeClass('cardstories_button_disabled');
                advertise_next.removeClass('cardstories_button_disabled');
            }

            // Bind countdown select.
            $('.cardstories_countdown_select', go_vote).unbind('change').change(function() {
                $this.send_countdown_duration($(this).val(), player_id, game.id, root);
            });

            // Bind go vote button, if possible.
            if (game.ready) {
                $('.cardstories_modal_button', go_vote).unbind('click').click(function() {
                    $this.animate_scale(true, 5, 300, go_vote, function() {
                        $this.invitation_owner_go_vote_confirm(player_id, game, element, root);
                    });
                });
            }

            // Mark advertise box as manually closed and hide FB like.
            var close_advertise = function() {
                advertise.addClass('cardstories_advertise_closed');
                $('.fb-like', advertise).hide();
            }
            advertise_close.click(close_advertise);
            advertise_next.click(close_advertise);

            var deferred = $.Deferred();
            var q = $this.create_queue(root);

            // Display the advertise modal automatically, if it wasn't manually closed.
            if (!advertise.hasClass('cardstories_advertise_closed')) {
                $(root).queue(q, function(next) {
                    $this.advertise(player_id, game.id, element, root);
                    next();
                });
            }

            // Then the invite friend buttons.
            $(root).queue(q, function(next) {
                $this.invitation_owner_slots_helper($('.cardstories_player_invite', element), player_id, game.id, element, root, next);
            });

            // Show players joining and picking cards.
            $(root).queue(q, function(next) {
                $this.invitation_owner_join_helper(player_id, game, element, root, next);
            });

            // Resolve deferred.
            $(root).queue(q, function(next) {
                deferred.resolve();
            });

            $(root).dequeue(q);

            return deferred;
        },

        invitation_owner_slots_helper: function(slots, player_id, game_id, element, root, cb) {
            var $this = this;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_player_invite', snippets);
            var last = slots.length - 1;
            slots.each(function(i) {
                var slot = $(this);

                if (slot.hasClass('cardstories_noop')) {
                    if (i === last) {
                        cb();
                    }
                } else {
                    slot.addClass('cardstories_noop');

                    // If the coresponding player seat is already visible (the player already joined),
                    // don't show the invite slot.
                    var seat = $('.cardstories_player_seat.cardstories_player_seat_' + (i + 1), element);
                    if (!seat.is(':visible')) {
                        // Copy over the snippet first.
                        slot_snippet.clone().children().appendTo(slot);

                        // Bind click behavior.
                        slot.unbind('click').click(function() {
                            $this.advertise(player_id, game_id, element, root);
                        });

                        // Finally animate it in.
                        $this.animate_scale(false, 5, 300, slot, function() {
                            if (i === last) {
                                cb();
                            }
                        });
                    }
                }
            });
        },

        invitation_owner_join_helper: function(player_id, game, element, root, cb) {
            var $this = this;
            var players = game.players;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_player_seat', snippets);
            var last = players.length - 1;
            var progress = $('.cardstories_progress', element);
            var go_vote = $('.cardstories_go_vote', element);

            var delay_next = false;
            var play_sound = true;
            var slotno = 0;
            var picked = 0;
            var q = $this.create_queue(root);
            $.each(players, function(i, player) {
                var playerq = $this.create_queue(root);

                // Delay this player, but only if there was at least one change
                // displayed for the previous ones.
                if (delay_next) {
                    $this.delay(root, 350, q);
                    delay_next = false;
                }

                // Skip the owner.
                if (player.id != game.owner_id) {
                    slotno++;
                    // Animate the progress bar as soon as one player joins.
                    // Do it in parallel with the other animations.
                    if (!progress.hasClass('cardstories_noop')) {
                        progress.addClass('cardstories_noop');
                        $(root).queue(playerq, function(next) {
                            $this.animate_progress_bar(4, element);
                            next();
                        });
                    }

                    // Show the go-to-vote box as soon as one player joins,
                    // also in parallel, and hide the modal, if it's visible.
                    if (!go_vote.hasClass('cardstories_noop_show')) {
                        go_vote.addClass('cardstories_noop_show');
                        $(root).queue(playerq, function(next) {
                            $this.animate_scale(false, 5, 300, go_vote);
                            next();
                        });
                    }

                    var pick_sprite = $('.cardstories_player_pick_' + slotno, element);

                    // Set up the player seat and joining animation.
                    var slot = $('.cardstories_player_seat.cardstories_player_seat_' + slotno, element);
                    if (!slot.hasClass('cardstories_noop_join')) {
                        slot.addClass('cardstories_noop_join');
                        delay_next = true;
                        slot_snippet.clone().children().appendTo(slot);
                        slot.addClass('cardstories_player_seat_joined');
                        var player_info = $this.get_player_info_by_id(player.id);
                        $this.display_player_info(player_info, slot);
                        $('.cardstories_player_status', slot).html('joined the game!');

                        if (play_sound) {
                            $.cardstories_audio.play('join', root);
                            play_sound = false;
                        }

                        // Artificial delay between joining and picking.
                        $this.delay(root, 300, playerq);
                    }

                    // Show the join sprite animation (cards being dealt, hands coming out).
                    if (!slot.hasClass('cardstories_noop_sprite')) {
                        slot.addClass('cardstories_noop_sprite');
                        var invite_slot = $('.cardstories_player_invite.cardstories_player_seat_' + slotno, element);
                        var join_sprite = $('.cardstories_player_join_' + slotno, element);
                        var player_arms = $('.cardstories_player_arms_' + slotno, element);
                        // Queue the animation.
                        $(root).queue(playerq, function(next) {
                            invite_slot.fadeOut();
                            slot.show();
                            $this.animate_sprite(join_sprite, 18, 18, false, false, function() {
                                player_arms.show();
                                pick_sprite.show();
                                join_sprite.hide();
                                next();
                            });
                        });
                    }

                    // If the player hasn't picked a card, show the "picking"
                    // state, but only if it hasn't been shown before.  The
                    // same goes for the picked state: if a player has picked a
                    // card and the animation has been shown, don't do it
                    // again.
                    if (player.picked === null) {
                        if (!slot.hasClass('cardstories_noop_picking')) {
                            slot.addClass('cardstories_noop_picking');
                            delay_next = true;
                            $(root).queue(playerq, function(next) {
                                slot.removeClass('cardstories_player_seat_joined');
                                slot.addClass('cardstories_player_seat_picking');
                                $('.cardstories_player_status', slot).html('is picking a card<br />...');
                                next();
                            });
                        }
                    } else {
                        if (!slot.hasClass('cardstories_noop_picked')) {
                            slot.addClass('cardstories_noop_picked');
                            delay_next = true;
                            $(root).queue(playerq, function(next) {
                                slot.addClass('cardstories_player_seat_picked');
                                $('.cardstories_player_status', slot).html('has picked a card!');
                                $this.animate_sprite(pick_sprite, 18, 7, false, false, function() {
                                    pick_sprite.find('.cardstories_card').show();
                                    next();
                                });
                            });
                        }

                        // Only visually enable the button after the second
                        // picked card animation, to match server logic.
                        picked++;
                        if (game.ready && picked == 2) {
                            $(root).queue(playerq, function(next) {
                                // Start the countdown.
                                var countdown_select = go_vote.find('.cardstories_countdown_select');
                                $this.start_countdown(game.countdown_finish, countdown_select);
                                // Enable the button.
                                if (!go_vote.hasClass('cardstories_noop_enable')) {
                                    go_vote.addClass('cardstories_noop_enable');
                                    var b = go_vote.find('.cardstories_modal_button');
                                    b.removeClass('cardstories_button_disabled');
                                    b.find('span').html('GO TO VOTE');
                                }
                                next();
                            });
                        }
                    }
                }

                // If this is the last player, insert our on-complete callback.
                if (i === last) {
                    $(root).queue(playerq, function(next) {cb();});
                }

                // Queue the dequeueing of this player's queue. ;)
                $(root).queue(q, function(next) {
                    $(root).dequeue(playerq);
                    next();
                });
            });

            $(root).dequeue(q);
        },

        invitation_owner_go_vote_confirm: function(player_id, game, element, root) {
            var $this = this;
            var modal = $('.cardstories_go_vote_confirm', element);
            var overlay = $('.cardstories_modal_overlay', element);

            // Keep track of players who haven't picked a card yet
            var players_not_ready = 0;
            for(var i=0; i<game.players.length; i++) {
                if(game.players[i].picked === null) {
                    players_not_ready += 1;
                }
            }

            // If some players haven't picked a card, ask the GM to confirm
            if(players_not_ready > 0) {
                $this.display_modal(modal, overlay);

                $('.cardstories_go_vote_confirm_no', modal).unbind('click').click(function() {
                    $this.close_modal(modal, overlay, function() {
                        $this.animate_scale(false, 5, 300, $('.cardstories_go_vote', element));
                    });
                });

                $('.cardstories_go_vote_confirm_yes', modal).unbind('click').click(function() {
                    $this.close_modal(modal, overlay, function() {
                        $this.invitation_owner_go_to_vote_animate(player_id, game, element, root);
                    });
                });
            } else {
                $this.invitation_owner_go_to_vote_animate(player_id, game, element, root);
            }
        },

        invitation_owner_go_to_vote_animate: function(player_id, game, element, root) {
            var $this = $.cardstories;
            var players = game.players;
            var nr_of_slots = players.length - 1;
            var q = $this.create_queue(root);
            for (var i=0, slotno=0; i < players.length; i++) {
                if (players[i].id != game.owner_id) {
                    slotno++;

                    // Insert an artificial delay between players, for
                    // aesthetical reasons.
                    if (slotno > 1) {
                        $this.delay(root, 350, q);
                    }

                    $(root).queue(q, (function(slotno) {return function(next) {
                        $('.cardstories_player_pick_' + slotno, element).addClass('cardstories_no_background');
                        var return_sprite = $('.cardstories_player_return_' + slotno, element);
                        var is_last_slot = slotno === nr_of_slots;
                        $this.animate_sprite(return_sprite, 18, 18, false, false, function() {
                            return_sprite.hide();
                            if (is_last_slot) { next(); }
                        });
                        if (!is_last_slot) { next(); }
                    };})(slotno));
                }
            }

            $(root).queue(q, function(next) {
                $this.animate_progress_bar(5, element);
                var cards = $('.cardstories_player_pick .cardstories_card', element);
                cards.each(function(i) {
                    var card = $(this);
                    var final_left = card.metadata({type: 'attr', name: 'data'}).final_left;
                    var cb = function() {
                        if (i === cards.length - 1) {
                            next();
                        }
                    };
                    card.animate({left: final_left}, 500, cb);
                });
            });

            // Queue the state change.
            $(root).queue(q, function(next) {
                $this.send({
                    action: 'voting',
                    owner_id: player_id,
                    game_id: game.id
                }, function() {
                    $this.game(player_id, game.id, root);
                }, player_id, game.id, root);
            });

            $(root).dequeue(q);
        },

        invitation_pick: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick', root);
            this.set_active('invitation_pick', element, root, game);
            this.display_progress_bar('player', 1, element, root);
            this.display_master_info($this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);

            // Send picked card when the user clicks ok.
            var ok = function(card_value, card_index) {
                var query = {
                    action: 'pick',
                    player_id: player_id,
                    game_id: game.id,
                    card: card_value
                };
                var callback = function() {
                    $this.game(player_id, game.id, root);
                };
                var onerror = function(error) {
                    if (error.code === 'WRONG_STATE_FOR_PICKING' && error.data.state === 'vote') {
                        $this.show_warning('.cardstories_picked_too_late', player_id, game.id, root, callback);
                    } else {
                        $this.panic(error, player_id, game.id, root);
                    }
                };
                $this.invitation_pick_confirm_helper(player_id, game, card_index, card_value, element, root, function() {
                    $this.send(query, callback, player_id, game.id, root, {onerror: onerror});
                });
            };

            // Display the board.
            this.create_invitation_display_board(player_id, game, element, root, false);

            var deferred = $.Deferred();
            var resolve = false;
            var q = $this.create_queue(root);

            // Only show initial animations once.
            if (!element.hasClass('cardstories_noop_init')) {
                element.addClass('cardstories_noop_init');

                // Show a replay of the author picking a card and writing a sentence.
                $(root).queue(q, function(next) {
                    $this.replay_create_game(game, element, root, next);
                });

                // Show players being dealt cards.
                $(root).queue(q, function(next) {
                    $this.invitation_pick_deal_helper(game, element, root, next);
                });

                // Move card and sentence box to final positions.
                $(root).queue(q, function(next) {
                    $this.invitation_pick_card_box_helper(element, root, next);
                });

                // Show the modal info box.
                $(root).queue(q, function(next) {
                    $this.display_modal($('.cardstories_info', element), $('.cardstories_modal_overlay', element), null, next);
                });

                // Morph cards into dock.
                var card_specs = $.map(game.self[2], function(card, index) { return {'value': card}; });
                $(root).queue(q, function(next) {
                    $this.invitation_pick_dock_helper(player_id, game, card_specs, element, root, next);
                });

                // Set up the dock itself and continue immediately, so the
                // player can see others joining while he picks his cards.
                $(root).queue(q, function(next) {
                    $this.select_cards('invitation_pick', card_specs, ok, element, root).done(function() {
                        deferred.resolve();
                    });
                    next();
                });
            } else {
                resolve = true;
            }

            // Once the player's set up, update board status as players join.
            $(root).queue(q, function(next) {
                $this.create_invitation_display_board(player_id, game, element, root, true);
                $this.invitation_pick_deal_helper(game, element, next);
            });

            // Resolve deferred, if we're not initializing.
            if (resolve) {
                $(root).queue(q, function(next) {
                    deferred.resolve();
                });
            }

            $(root).dequeue(q);

            return deferred;
        },

        invitation_pick_confirm_helper: function(player_id, game, card_index, card_value, element, root, cb) {
            var $this = this;
            var hand = $('.cardstories_cards_hand', element);
            var docked_cards = $('.cardstories_card', hand);
            var container = $('.cardstories_card_backs', element);
            var cards = $('img', container);
            var board = $('.cardstories_board', element);
            var last = cards.length - 1;
            var flyover = $('.cardstories_card_flyover', element);

            var q = $this.create_queue(root);
            var q2 = $this.create_queue(root);

            container.show();
            cards.each(function(i) {
                var card = $(this);
                var cardq = $this.create_queue(root);
                var j = last - i;
                var docked_card = docked_cards.eq(j);
                var docked_card_foreground = docked_card.find('.cardstories_card_foreground');

                // If this is the selected card, replace it with one positioned
                // absolutely to the board.
                if (card_index === j) {
                    card.hide();
                    var meta = flyover.metadata({type: 'attr', name: 'data'});
                    var src = meta.card.supplant({card: card_value});
                    $('.cardstories_card_foreground', flyover).attr('src', src);
                    flyover.css({
                        width: docked_card_foreground.width(),
                        height: docked_card_foreground.height(),
                        top: docked_card_foreground.offset().top - board.offset().top,
                        left: docked_card_foreground.offset().left - board.offset().left,
                        zIndex: docked_card.css('z-index')
                    });
                    flyover.show();
                } else {
                    // Save initial pos.
                    var init_pos = {
                        width: card.width(),
                        height: card.height(),
                        top: card.position().top,
                        left: card.position().left
                    };

                    // Calculate starting position absolutely to the container.
                    var start_pos = {
                        width: docked_card_foreground.width(),
                        height: docked_card_foreground.height(),
                        top: docked_card_foreground.offset().top - container.offset().top,
                        left: docked_card_foreground.offset().left - container.offset().left,
                        zIndex: docked_card.css('z-index')
                    };

                    // Set the card's properties.
                    card.css(start_pos);

                    // Animate back to initial position.
                    $(root).queue(cardq, function(next) {
                        card.animate(init_pos, 250, next);
                    });

                    // Morph out...
                    $(root).queue(cardq, function(next) {
                        card.animate({width: 0, left: init_pos.left + (init_pos.width / 2)}, 250, next);
                    });

                    // ... and then back in.
                    $(root).queue(cardq, function(next) {
                        var src = card.metadata({type: 'attr', name: 'data'}).nocard;
                        card.attr('src', src);
                        card.animate(init_pos, 250, next);
                    });
                }

                // If this is the last one, dequeue stage 2.
                if (card_index === 0) {
                    if (i === (last - 1)) {
                        $(root).queue(cardq, function(next) {
                            $(root).dequeue(q2);
                        });
                    }
                } else if (i === last) {
                    $(root).queue(cardq, function(next) {
                        $(root).dequeue(q2);
                    });
                }

                $(root).queue(q, function(next) {
                    $(root).dequeue(cardq);
                    next();
                });
            });

            // Hide the dock, we don't need it anymore.
            hand.hide();

            var seat_nb = $this.get_player_seat_nb(player_id, game);
            var hand2dock_sprite = $('.cardstories_player_hand2dock_' + seat_nb, element);
            var overlay = $('.cardstories_modal_overlay', element);
            $(root).queue(q2, function(next) {
                hand2dock_sprite.show();
                container.hide();
                overlay.fadeOut('fast');
                $this.animate_sprite(hand2dock_sprite, 18, 18, true, false, next);
            });

            // Move card back and change seat status.
            var pick_sprite = $('.cardstories_player_pick_' + seat_nb, element);
            var pick_card =  $('.cardstories_card', pick_sprite);
            $(root).queue(q2, function(next) {
                pick_sprite.show();
                pick_card.show();
                var end_pos = {
                    width: pick_card.width(),
                    height: pick_card.height(),
                    top: pick_card.offset().top - board.offset().top,
                    left: pick_card.offset().left - board.offset().left
                };
                pick_card.hide();
                pick_sprite.hide();
                flyover.animate(end_pos, 300, next);
            });

            $(root).queue(q2, function(next) {
                // Set player status
                var slot = $('.cardstories_player_seat_' + seat_nb, element);
                $('.cardstories_player_status', slot).html('has picked a card!');

                // Set last state of the sprite.
                var x = -(6 * pick_sprite.width());
                pick_sprite.css({'background-position': x + 'px 0px'});
                pick_sprite.show();
                hand2dock_sprite.fadeOut('normal', next);
            });

            $(root).queue(q2, function(next) {
                $this.animate_progress_bar(2, element, next);
            });

            if (cb) {
                $(root).queue(q2, function(next) {cb();});
            }

            $(root).dequeue(q);
        },

        replay_create_game: function(game, element, root, cb) {
            var $this = this;
            var deck = $('.cardstories_deck', element);
            var cards = $('.cardstories_card', deck);
            var hand = $('.cardstories_master_hand', element);
            var meta = hand.metadata({type: "attr", name: "data"});
            var dock = $('.cardstories_master_cards', hand);
            var deck_cover = $('.cardstories_deck_cover', deck);
            var wait_for_card_modal = $('.cardstories_wait_for_card', element);
            var wait_for_sentence_modal = $('.cardstories_wait_for_sentence', element);
            var overlay = $('.cardstories_modal_overlay', element);

            deck_cover.show();
            var final_pos = {
                width: deck_cover.width(),
                height: deck_cover.height(),
                top: deck_cover.position().top,
                left: deck_cover.position().left
            };
            deck_cover.hide();

            var q = $this.create_queue(root);

            // Start by dealing cards.
            // Make sure to only run the deal animation once.
            if (!element.hasClass('cardstories_deal_noop')) {
                element.addClass('cardstories_deal_noop');

                // Start by dealing cards.
                $(root).queue(q, function(next) {
                    $this.create_pick_card_animate_fly_to_board(cards, element, root, next);
                });

                // Dockify the cards, using the jqDock "trick" to get cards to overlap:
                // http://www.wizzud.com/jqDock/examples/example.php?f=jigsaw
                // Only expand the dock after it's been set up.
                $(root).queue(q, function(next) {
                    var active_card = $('img', dock).eq(meta.active);
                    var count = dock.children().length;
                    var options = {
                        size: meta.size,
                        distance: meta.distance,
                        setLabel: function(t, i, el) {
                            $('<img class="cardstories_card_foreground" src="' + t + '" alt="">')
                                .css({zIndex: count - i})
                                .appendTo($(el).parent().css({zIndex: 2 * (count - i)}));
                            return false;
                        },
                        onReady: function(ready) {
                            active_card.jqDock('expand');
                            // jqDock doesn't provide a hook for when expansion
                            // finishes, so use a timeout to call next().
                            $this.animationTimeout(function() {
                                if (game.winner_card === null && !wait_for_card_modal.hasClass('cardstories_noop')) {
                                    $this.display_modal(wait_for_card_modal, overlay);
                                }
                                next();
                            }, 500);
                        }
                    };
                    dock.jqDock(options);
                });
            }

            // Animate chosen card (raise it up), and move other cards back to the deck.
            // Only run the animation if the card has already been set,
            // and the animation hasn't yet been run.
            if (game.winner_card !== null && !element.hasClass('cardstories_choose_noop')) {
                element.addClass('cardstories_choose_noop');

                // If the wait_for_card modal is displayed, close it first.
                $(root).queue(q, function(next) {
                    // Mark the modal with a 'noop' class, to prevent it from being displayed again
                    // (it could happen when there's multiple concurrently running
                    // replay_create_game functions).
                    wait_for_card_modal.addClass('cardstories_noop');
                    if (wait_for_card_modal.is(':visible')) {
                        $this.close_modal(wait_for_card_modal, overlay, next);
                    } else {
                        next();
                    }
                });

                // Reposition selected card.
                var original_pos;
                $(root).queue(q, function(next) {
                    var docked_cards = $('.cardstories_card', hand);

                    // Substitute docked cards with absolute positioned ones.
                    cards.each(function(i) {
                        var card = $(this);
                        var docked_card = docked_cards.find('.cardstories_card_foreground').eq(i);
                        card.css({
                            width: docked_card.width(),
                            height: docked_card.height(),
                            top: card.position().top - docked_card.height() + final_pos.height,
                            left: docked_card.offset().left - deck.offset().left,
                            zIndex: docked_card.css('z-index')
                        });

                        // Bring selected card to front.
                        if (i === meta.active) {
                            card.css({zIndex: 20});
                        }

                        // Hide docked version.
                        docked_card.hide();
                    });

                    // Center and enlarge selected card, saving original pos.
                    var c = cards.eq(meta.active);
                    original_pos = {
                        width: c.width(),
                        height: c.height(),
                        top: c.position().top,
                        left: c.position().left
                    };
                    var l = c.position().left - ((meta.w - c.width())/2);
                    c.animate({
                        width: meta.w,
                        height: meta.h,
                        top: meta.t,
                        left: l
                    }, 500, next);
                });

                // Animate other cards back to deck.
                $(root).queue(q, function(next) {
                    var last = cards.length - 1;
                    if (last == meta.active) {
                        last -= 1;
                    }
                    var cardq = $this.create_queue(root);
                    cards.each(function(i) {
                        // Skip selected one.
                        if (i !== meta.active) {
                            var card = $(this);

                            // The first card should start flying immediately,
                            // but each subsequent card should be delayed.
                            if (i !== 0) {
                                $this.delay(root, 100, cardq);
                            }

                            $(root).queue(cardq, function(inner_next) {
                                card.animate(final_pos, 500, function() {
                                    card.hide();
                                    if (i === last) {
                                        next();
                                    }
                                });
                                inner_next();
                            });
                        }
                    });

                    $(root).dequeue(cardq);
                });

                // Move selected card back down.
                $(root).queue(q, function(next) {
                    var card = cards.eq(meta.active);
                    card.animate(original_pos, 500, next);
                });

                // Display the wait_for_sentence modal, but only if the sentence hasn't
                // yet been set.
                $(root).queue(q, function(next) {
                    if (game.sentence === null && !wait_for_sentence_modal.hasClass('cardstories_noop')) {
                        $this.display_modal(wait_for_sentence_modal, overlay, next);
                    } else {
                        next();
                    }
                });
            }

            // Show the story.
            // But only do it if the story has already been set.
            if (game.sentence !== null) {
                // If the wait_for_sentence modal is visible, hide it first.
                $(root).queue(q, function(next) {
                    // Mark the modal with a 'noop' class, to prevent it from being displayed again
                    // (it could happen when there's multiple concurrently running
                    // replay_create_game functions).
                    wait_for_sentence_modal.addClass('cardstories_noop');
                    if (wait_for_sentence_modal.is(':visible')) {
                        $this.close_modal(wait_for_sentence_modal, overlay, next);
                    } else {
                        next();
                    }
                });

                // Show story.
                $(root).queue(q, function(next) {
                    $('.cardstories_sentence_box', element).fadeIn('normal', function() {
                        $(this).show(); // A workaround for http://bugs.jquery.com/ticket/8892
                        next();
                    });
                });
            }

            $(root).queue(q, function(next) {
                if (cb) {
                    cb();
                }
            });

            $(root).dequeue(q);
        },

        invitation_pick_deal_helper: function(game, element, root, cb) {
            var $this = this;
            var last = game.players.length - 1;
            var q = $this.create_queue(root);
            var delay_next = false;
            for (var i=0, seat_nb=0; i < game.players.length; i++) {
                var playerq = $this.create_queue(root);

                // Delay this player, but only if there was at least one change
                // displayed for the previous ones.
                if (delay_next) {
                    $this.delay(root, 350, q);
                    delay_next = false;
                }

                // Skip the owner.
                if (game.players[i].id != game.owner_id) {
                    seat_nb++;

                    // Joining animation.
                    var seat = $('.cardstories_player_seat.cardstories_player_seat_' + seat_nb, element);
                    if (!seat.hasClass('cardstories_noop_join')) {
                        seat.addClass('cardstories_noop_join');
                        delay_next = true;
                        $(root).queue(playerq, (function(seat, seat_nb) {return function(next) {
                            var join_sprite = $('.cardstories_player_join_' + seat_nb, element);
                            $this.animate_sprite(join_sprite, 18, 18, false, false, function() {
                                $('.cardstories_player_arms_' + seat_nb, element).show();
                                $('.cardstories_player_pick_' + seat_nb, element).show();
                                join_sprite.hide();
                                next();
                            });
                        };})(seat, seat_nb));
                    }
                }

                // If this is the last player, insert our on-complete callback.
                if (i === last) {
                    $(root).queue(playerq, function(next) {
                        if (cb) {
                            cb();
                        }
                    });
                }

                // Queue the dequeueing of this player's queue. ;)
                $(root).queue(q, (function(playerq) {return function(next) {
                    $(root).dequeue(playerq);
                    next();
                };})(playerq));
            }

            $(root).dequeue(q);
        },

        invitation_pick_card_box_helper: function(element, root, cb) {
            var $this = this;
            var dest_element = $('.cardstories_invitation .cardstories_pick_wait', root);
            var dest_sentence = $('.cardstories_sentence_box', dest_element);
            var dest_card = $('.cardstories_picked_card', dest_element);
            var sentence = $('.cardstories_sentence_box', element);
            var active = $('.cardstories_master_hand', element).metadata({type: "attr", name: "data"}).active;
            var card = $('.cardstories_deck .cardstories_card', element).eq(active);

            // Grab final pos
            dest_element.show();
            var sentence_pos = {
                top: dest_sentence.position().top,
                left: dest_sentence.position().left
            };
            // For the card, we must compensate for the board, since it is
            // actually inside the deck.
            var card_pos = {
                width: dest_card.width(),
                height: dest_card.height(),
                top: dest_card.position().top,
                left: dest_card.position().left + $('.cardstories_board', element).position().left
            };
            dest_element.hide();

            // Move them in parallel.
            sentence.animate(sentence_pos, 500);
            card.animate(card_pos, 500, cb);
        },

        get_player_seat_nb: function(player_id, game) {
            // What's the number (position) of the player seat on this game?

            var seat_nb=0;
            for (var i=0; i < game.players.length; i++) {
                if (game.owner_id != game.players[i].id) {
                    seat_nb++;
                    if (player_id == game.players[i].id) {
                        break;
                    }
                }
            }

            return seat_nb;
        },

        invitation_pick_dock_helper: function(player_id, game, card_specs, element, root, cb) {
            var $this = this;
            var container = $('.cardstories_card_backs', element);
            var cards = $('img', container);
            var last = cards.length - 1;
            var src_template = $('.cardstories_cards_hand .cardstories_card_template', element).metadata({type: 'attr', name: 'data'}).card;
            var turnaround_duration = 600;

            // Save initial positions, calculate intermediate ones.
            container.show();
            var init_pos = [];
            var mid_pos = [];
            cards.each(function(i) {
                var card = $(this);
                init_pos.push({
                    width: card.width(),
                    left: card.position().left
                });
                mid_pos.push({
                    width: 0,
                    left: card.position().left + card.width()/2
                });
            });
            container.hide();

            var seat_nb = $this.get_player_seat_nb(player_id, game);
            var hand2dock_sprite = $('.cardstories_player_hand2dock_' + seat_nb, element);
            var pick_sprite = $('.cardstories_player_pick_' + seat_nb, element);

            var q = $this.create_queue(root);

            // Deal cards from hands to dock.
            $(root).queue(q, function(next) {
                pick_sprite.hide();
                hand2dock_sprite.show();
                $this.animate_sprite(hand2dock_sprite, 18, 19, false, false, next);
            });

            // Morph cards out, switching image to actual right one.  At the
            // same time, show milky modal overlay.
            $(root).queue(q, function(next) {
                hand2dock_sprite.hide();
                container.show();
                $('.cardstories_modal_overlay', element)
                    .addClass('milk')
                    .fadeIn(turnaround_duration);
                cards.each(function(i) {
                    var card = $(this);
                    card.animate(mid_pos[i], turnaround_duration/2, function() {
                        var foreground_src = src_template.supplant({card: card_specs[last - i].value});
                        card.attr('src', foreground_src).addClass('cardstories_card_border');
                        if (i === last) {
                            next();
                        }
                    });
                });
            });

            // Morph cards back in, using original positions.
            $(root).queue(q, function(next) {
                cards.each(function(i) {
                    var card = $(this);
                    card.animate(init_pos[i], turnaround_duration/2, function() {
                        if (i === last) {
                            next();
                        }
                    });
                });
            });

            $(root).queue(q, function(next) {
                if (cb) {
                    cb();
                }
            });

            $(root).dequeue(q);
        },

        invitation_pick_wait: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick_wait', root);
            var deferred = $.Deferred();
            this.set_active('invitation_pick_wait', element, root, game);
            element.show(); // Because it was hidden in invitation_pick_card_box_helper.
            $('.cardstories_sentence', element).text(game.sentence);

            this.display_progress_bar('player', 2, element, root);
            this.display_master_info($this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);
            this.create_invitation_display_board(player_id, game, element, root, false);

            var modal = $('.cardstories_modal', element);
            var overlay = $('.cardstories_modal_overlay', element);
            this.display_modal(modal, overlay);

            this.invitation_pick_wait_picked_helper(player_id, game, element, root, function() {
                deferred.resolve();
            });

            return deferred;
        },

        select_cards: function(id, cards, ok, element, root) {
            var $this = this;
            var confirm = $('.cardstories_card_confirm', element);
            if (confirm.children().length == 0) {
                var snippets = $('.cardstories_snippets', root);
                var confirm_snippet = $('.cardstories_card_confirm', snippets);
                confirm_snippet.clone().children().appendTo(confirm);
            }
            var confirm_callback = function(card, index, nudge, cards_element) {
                $this.animate_scale(false, 5, 300, confirm);
                $('.cardstories_card_confirm_ok', confirm).unbind('click').click(function() {
                    $this.animate_scale(true, 5, 300, confirm, function() {
                        ok(card, index);
                        nudge(true);
                    });
                });
                $('.cardstories_card_confirm_cancel', confirm).unbind('click').click(function() {
                    $this.animate_scale(true, 5, 300, confirm, function() {
                        nudge(false);
                    });
                });
            };
            var hand = $('.cardstories_cards_hand', element);
            return this.display_or_select_cards(id, cards, confirm_callback, hand, root, true);
        },

        display_or_select_cards: function(id, cards, select_callback, element, root, start_collapsed) {
            var elem_id = id + '_saved_element';
            var $root = $(root);
            var saved_elements = $root.data('cardstories_saved_elements') || {};
            if (saved_elements[elem_id] === undefined) {
                saved_elements[elem_id] = element.html();
                $root.data('cardstories_saved_elements', saved_elements);
            } else {
                element.html(saved_elements[elem_id]);
            }
            var meta = element.metadata({type: "attr", name: "data"});
            var active_card = meta.active;
            var options = {
                'size': meta.size,
                'distance': meta.distance
            };
            if (start_collapsed !== true) {
                options.active = active_card;
            }
            var template = $('.cardstories_card_template', element);
            var dock = $('.cardstories_cards', element);
            var deferred = $.Deferred();
            options.onReady = function(is_ready) {
                var links = $('a.cardstories_card', element);
                // There is some trickery involved here. We need to hold a reference to the
                // active_card_img so that we can expand it later (if starting collapsed).
                // In the loop below, the images will be replaced and because jqDock only keeps
                // a reference to the original images present at initialization time,
                // we wouldn't be able to expand it without this reference.
                var active_card_img = start_collapsed ? $('img', links).eq(active_card) : null;
                var html = template.html();
                var meta = template.metadata({type: "attr", name: "data"});
                links.each(function(index) {
                    var link = $(this);
                    var card = cards[index];
                    var card_file = meta.nocard;
                    if (index < cards.length && card !== null && card.value !== null) {
                        card_file = meta.card.supplant({'card': card.value});
                    }
                    var label = card && card.label ? card.label : '';
                    link.html(html.supplant({ 'label': label }));
                    var zindex = 3 * (links.length - index);
                    link.css({zIndex: zindex});
                    var background = $('.cardstories_card_background', link);
                    var has_bg = meta.card_bg && meta.card_bg.length > 0;
                    if (has_bg) {
                        background.attr('src', meta.card_bg);
                    } else if (background.attr('src') !== undefined) {
                        background.removeAttr('src');
                    }
                    background.css({zIndex: links.length - index});
                    var foreground = $('.cardstories_card_foreground', link);
                    foreground.attr('src', card_file).css({zIndex: 2 * (links.length - index)});
                    if (card) {
                        link.toggleClass('cardstories_card_inactive', card.inactive !== undefined);
                    }
                    if (select_callback && card && card.inactive === undefined) {
                        link.metadata({type: "attr", name: "data"}).card = card.value;
                        link.unbind('click').click(function() {
                            if(!$('a.cardstories_card', element).hasClass('cardstories_card_selected')) {
                                link.addClass('cardstories_card_selected');
                                link.css({zIndex: 200});
                                var nudge = function(confirmed) {
                                    // In 'create_pick_card', we don't want the dock restored
                                    // after confirming the card, so omit these steps in that case.
                                    if (!(confirmed && id === 'create_pick_card')) {
                                        link.removeClass('cardstories_card_selected');
                                        link.css({zIndex: zindex});
                                        if (has_bg) {
                                            background.attr('src', meta.card_bg);
                                        } else {
                                            background.removeAttr('src');
                                        }
                                    }
                                    dock.jqDock('nudge');
                                };
                                background.attr('src', meta.card_bg_selected);
                                dock.jqDock('freeze');
                                $(this).blur();
                                select_callback.call(this, card.value, index, nudge, element);
                            }
                        });
                    }
                });
                dock.show();
                if (start_collapsed) {
                    active_card_img.jqDock('expand');
                }
                deferred.resolve(is_ready);
            };

            dock.jqDock(options);

            return deferred;
        },

        player_participate: function(player_id, game, root) {
            var $this = this;
            var query = {
                action: 'participate',
                player_id: player_id,
                game_id: game.id
            };
            var callback = function() {
                $this.game(player_id, game.id, root);
            };
            var onerror = function(error) {
                if (error.code === 'GAME_FULL') {
                    $this.show_warning('.cardstories_game_full', player_id, game.id, root, function() {
                        $this.reload(player_id, game.id, {anonymous: true}, root);
                    });
                } else {
                    $this.panic(error, player_id, game.id, root);
                }
            };
            $this.send(query, callback, player_id, game.id, root, {onerror: onerror});

            return $.Deferred().resolve();
        },

        invitation_anonymous: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick', root);
            this.set_active('invitation_anonymous', element, root, game);
            this.display_progress_bar('player', 2, element, root);
            this.display_master_info($this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);
            this.create_invitation_display_board(player_id, game, element, root, false);

            var deferred = $.Deferred();
            var q = $this.create_queue(root);

            // Only show initial animations once.
            if (!element.hasClass('cardstories_noop_init')) {
                element.addClass('cardstories_noop_init');

                // Show a replay of the author picking a card and writing a sentence.
                $(root).queue(q, function(next) {
                    $this.replay_create_game(game, element, root, next);
                });

                // Show players being dealt cards.
                $(root).queue(q, function(next) {
                    $this.invitation_pick_deal_helper(game, element, root, next);
                });

                // Move card and sentence box to final positions.
                $(root).queue(q, function(next) {
                    $this.invitation_pick_card_box_helper(element, root, next);
                });
            } else {
                $(root).queue(q, function(next) {
                    $this.invitation_pick_deal_helper(game, element, root, next);
                });
            }

            $(root).queue(q, function(next) {
                $this.invitation_pick_wait_picked_helper(player_id, game, element, root, next);
            });

            $(root).queue(q, function(next) {
                deferred.resolve();
            });

            $(root).dequeue(q);

            return deferred;
        },

        create_invitation_display_board: function(player_id, game, element, root, set_status) {
            $('.cardstories_sentence', element).text(game.sentence);
            var $this = this;
            var players = game.players;
            var snippets = $('.cardstories_snippets', root);
            var seat_snippet = $('.cardstories_player_seat', snippets);
            for (var i=0, seat_nb=0; i < players.length; i++) {
                if (players[i].id != game.owner_id) {
                    seat_nb++;

                    // Only initialize the seat once.
                    var seat = $('.cardstories_player_seat.cardstories_player_seat_' + seat_nb, element);
                    if (seat.children().length == 0) {
                        seat_snippet.clone().children().appendTo(seat);
                        var player_info = $this.get_player_info_by_id(players[i].id);
                        $this.display_player_info(player_info, seat);
                        seat.show();
                    }

                    var status = $('.cardstories_player_status', seat);
                    // Differentiate between player status.
                    if (players[i].id == player_id) {
                        seat.addClass('cardstories_player_seat_self');
                        if (set_status) {
                            status.html('is picking a card<br />...');
                        }
                    } else {
                        seat.addClass('cardstories_player_seat_joined');
                    }
                }
            }
        },

        invitation_pick_wait_picked_helper: function(player_id, game, element, root, cb) {
            var $this = this;
            var players = game.players;
            var last = players.length - 1;
            var q = $this.create_queue(root);
            var delay_next = false;

            for (var i=0, seat_nb=0; i < players.length; i++) {
                var playerq = $this.create_queue(root);

                // Skip the owner.
                if (players[i].id !== game.owner_id) {
                    seat_nb++;
                    var seat = $('.cardstories_player_seat.cardstories_player_seat_' + seat_nb, element);
                    var status = $('.cardstories_player_status', seat);

                    $('.cardstories_player_arms_' + seat_nb, element).show();
                    $('.cardstories_player_pick_' + seat_nb, element).show();

                    // Delay this player, but only if there was at least one change
                    // displayed for the previous ones.
                    if (delay_next) {
                        $this.delay(root, 350, q);
                        delay_next = false;
                    }

                    // Deferentiate between players who picked a card
                    // and those who didn't.
                    if (players[i].picked !== null) {
                        if (!seat.hasClass('cardstories_noop_picked')) {
                            seat.addClass('cardstories_noop_picked');
                            var card_img = $('.cardstories_player_pick_' + seat_nb, element).find('img');
                            if (players[i].id == player_id) {
                                var self_card = $('.cardstories_player_self_picked_card', element);
                                var foreground = $('.cardstories_card_foreground', self_card);
                                var src_template = foreground.metadata({type: 'attr', name: 'data'}).card;
                                foreground.attr('src', src_template.supplant({card: game.self[0]}));
                                // Copy card image final_left metadata.
                                var final_left = card_img.metadata({type: 'attr', name: 'data'}).final_left;
                                self_card.attr('data', '{final_left:' + final_left + '}');
                                card_img.replaceWith(self_card);
                                self_card.show();

                                // Set pick_sprite to final state.
                                var pick_sprite = $('.cardstories_player_pick_' + seat_nb, element);
                                var x = -(6 * pick_sprite.width());
                                pick_sprite.css({'background-position': x + 'px 0px'});
                            } else {
                                delay_next = true;
                                $(root).queue(playerq, (function(seat, seat_nb, card_img) { return function(next) {
                                    var pick_sprite = $('.cardstories_player_pick_' + seat_nb, element);
                                    $this.animate_sprite(pick_sprite, 18, 7, false, false, function() {
                                        pick_sprite.find('.cardstories_card').show();
                                        card_img.show();
                                        seat.addClass('cardstories_player_seat_waiting');
                                        next();
                                    });
                                };})(seat, seat_nb, card_img));
                            }
                            status.html('is waiting for other players<br />...');
                        }
                    } else {
                        seat.addClass('cardstories_player_seat_picking');
                        status.html('is picking a fake card<br />...');
                    }
                }

                // If this is the last player, insert our on-complete callback.
                if (i === last && cb) {
                    $(root).queue(playerq, function(next) {cb();});
                }

                // Queue the dequeueing of this player's queue. ;)
                $(root).queue(q, (function(playerq) {return function(next) {
                    $(root).dequeue(playerq);
                    next();
                };})(playerq));
            }

            $(root).dequeue(q);
        },

        vote: function(player_id, game, root) {
            var $this = this;
            var state = $(root).data('cardstories_state');
            var deferred;
            if (game.owner) {
                deferred = this.vote_owner(player_id, game, root);
            } else {
                if (game.self) {
                    if (game.self[1] === null) {
                        if (state && state.dom === 'invitation_pick_wait') {
                            deferred = this.invitation_pick_wait_to_vote_voter(player_id, state.game, game, root);
                        } else {
                            deferred = this.vote_voter(player_id, game, root);
                        }
                    } else {
                        deferred = this.vote_voter_wait(player_id, game, root);
                    }
                } else {
                    deferred = this.vote_anonymous(player_id, game, root);
                }
            }

            $this.poll({
                'type': ['game'],
                'game_id': game.id,
                'player_id': player_id
            }, player_id, game.id, root, function() {
                $this.game(player_id, game.id, root);
            });

            return deferred;
        },

        invitation_pick_wait_to_vote_voter: function(player_id, old_game, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick_wait', root);

            // Separate the seats between those whose players picked cards and
            // those who didn't.
            var active_seats = [];
            var absent_seats = $();
            for (var i=1; i < old_game.players.length; i++) {
                var found = false;
                for (var j=1; j < game.players.length; j++) {
                    if (old_game.players[i].id == game.players[j].id) {
                        found = true;
                        active_seats.push(i);
                        break;
                    }
                }
                if (!found) {
                    absent_seats = absent_seats
                        .add('.cardstories_player_seat_' + i, element)
                        .add('.cardstories_player_pick_' + i, element)
                        .add('.cardstories_player_arms_' + i, element);
                }
            }

            var deferred = $.Deferred();
            var q = $this.create_queue(root);

            // Close the modal first.
            var modal = $('.cardstories_modal', element);
            var overlay = $('.cardstories_modal_overlay', element);
            $(root).queue(q, function(next) {
                $this.close_modal(modal, overlay, next);
            });

            // Remove players who didn't pick a card from the board by fading them out.
            if (absent_seats.length) {
                $(root).queue(q, function(next) {
                    absent_seats.each(function(i) {
                        $(this).fadeOut(function() {
                            $(this).hide();
                            if (i === absent_seats.length - 1) {
                                next();
                            }
                        });
                    });
                });
            }

            $.each(active_seats, function(i, seat_nb) {
                // Insert an artificial delay between players, for
                // aesthetical reasons.
                if (i > 0) {
                    $this.delay(root, 350, q);
                }

                $(root).queue(q, function(next) {
                    $('.cardstories_player_pick_' + seat_nb, element).addClass('cardstories_no_background');
                    var return_sprite = $('.cardstories_player_return_' + seat_nb, element);
                    var is_last_seat = i === active_seats.length - 1;
                    $this.animate_sprite(return_sprite, 18, 18, false, false, function() {
                        return_sprite.hide();
                        if (is_last_seat) {
                            next();
                        }
                    });
                    if (!is_last_seat) {
                        next();
                    }
                });
            });

            $(root).queue(q, function(next) {
                $this.animate_progress_bar(3, element);
                var cards = $('.cardstories_player_pick .cardstories_card', element);
                cards.each(function(i) {
                    var card = $(this);
                    var final_left = card.metadata({type: 'attr', name: 'data'}).final_left;
                    var cb = function() {
                        if (i === cards.length - 1) {
                            next();
                        }
                    };
                    card.animate({left: final_left}, 500, cb);
                });
            });

            // Queue the state change.
            $(root).queue(q, function(next) {
                $this.vote_voter(player_id, game, root).done(function() {
                    deferred.resolve();
                });
            });

            $(root).dequeue(q);

            return deferred;
        },

        vote_voter: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_voter', root);
            this.set_active('vote_voter', element, root, game);
            $('.cardstories_sentence', element).text(game.sentence);
            this.display_progress_bar('player', 3, element, root);
            this.display_master_info($this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);

            // Send game when user clicks ok.
            var ok = function(card_index, card_value) {
                var query = {
                    action: 'vote',
                    player_id: player_id,
                    game_id: game.id,
                    card: card_value
                };
                var callback = function() {
                    $this.game(player_id, game.id, root);
                };
                var onerror = function(error) {
                    // If game has already completed in the meantime, it has been
                    // destroyed on the service, and the service will return a
                    // GAME_NOT_LOADED error.
                    if (error.code === 'GAME_NOT_LOADED') {
                        $this.show_warning('.cardstories_voted_too_late', player_id, game.id, root, callback);
                    } else {
                        $this.panic(error, player_id, game.id, root);
                    }
                };
                $this.animate_progress_bar(4, element, function() {
                    $this.send(query, callback, player_id, game.id, root, {onerror: onerror});
                });
            };

            // Update board state.
            this.vote_display_board(true, player_id, game, element, root);

            var deferred = $.Deferred();
            var q = $this.create_queue(root);

            if (!element.hasClass('cardstories_noop_init')) {
                element.addClass('cardstories_noop_init');

                // Supplant owner's name into modal.
                var info = $('.cardstories_info', element);
                var html = info.html().supplant({'name': $this.get_master_info(game).name});
                info.html(html);

                // Switch owner's card with card 6 (so it can be shuffled).
                var owner_card = $('.cardstories_picked_card', element);
                var card6 = $('img.cardstories_card_6', element);
                card6.css({
                    top: owner_card.position().top,
                    left: owner_card.position().left,
                    width: owner_card.width(),
                    height: owner_card.height()
                });
                owner_card.hide();
                card6.show();

                // Flip self card around.
                $(root).queue(q, function(next) {
                    var front = $('.cardstories_player_self_picked_card', element);
                    var back = $('.cardstories_player_self_picked_card_back', element);
                    $this.vote_flip_card(front, back, root, next);
                });

                // Shuffle the cards.
                $(root).queue(q, function(next) {
                    $this.vote_shuffle_cards(game, element, root, next);
                });

                // Show modal.
                $(root).queue(q, function(next) {
                    var overlay = $('.cardstories_modal_overlay', element);
                    $this.display_modal(info, overlay, null, next);
                });

                // Flip the cards out.
                $(root).queue(q, function(next) {
                    $this.vote_flip_out(game, element, next);
                });

                // Display cards.
                $(root).queue(q, function(next) {
                    $this.vote_display_or_select_cards(true, game.self[0], game, element, root, next, ok);
                });
            }

            // Resolve deferred.
            $(root).queue(q, function(next) {
                deferred.resolve();
            });

            $(root).dequeue(q);

            return deferred;
        },

        vote_voter_wait: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_voter_wait', root);
            this.set_active('vote_voter_wait', element, root, game);
            $('.cardstories_sentence', element).text(game.sentence);
            this.display_progress_bar('player', 4, element, root);
            this.display_master_info($this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);

            // Update board state.
            this.vote_display_board(false, player_id, game, element, root);

            var deferred = $.Deferred();
            var q = $this.create_queue(root);

            if (!element.hasClass('cardstories_noop_init')) {
                element.addClass('cardstories_noop_init');

                // Display cards.
                $(root).queue(q, function(next) {
                    $this.vote_display_or_select_cards(false, game.self[0], game, element, root, next);
                });

                // Show modal.
                $(root).queue(q, function(next) {
                    var selected = $('.cardstories_card_slot.selected', element);
                    var info = $('.cardstories_info', element);
                    var info_meta = info.metadata({type: 'attr', name: 'data'});
                    if (selected.hasClass('top')) {
                        info.css('top', info_meta.bottom);
                    } else {
                        info.css('top', info_meta.top);
                    }
                    $('.cardstories_modal_overlay', element).fadeIn(300);
                    $this.animate_scale(false, 5, 300, info, next);
                });
            }

            // Resolve deferred.
            $(root).queue(q, function(next) {
                deferred.resolve();
            });

            $(root).dequeue(q);

            return deferred;
        },

        vote_voter_wait_to_complete: function(player_id, old_game, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_voter_wait', root);
            var dest_element = $('.cardstories_complete', root);

            // Construct picked card => seat number translation, while also
            // finding out who didn't vote.
            var card2seat = {};
            var absent_seats = $();
            var i;
            for (i=0; i < old_game.players.length; i++) {
                var found = false;
                for (var j=0; j < game.players.length; j++) {
                    if (old_game.players[i].id == game.players[j].id) {
                        found = true;
                        card2seat[game.players[j].picked] = i;
                        break;
                    }
                }
                if (!found) {
                    absent_seats = absent_seats
                        .add('.cardstories_player_seat_' + i, element)
                        .add('.cardstories_player_arms_' + i, element);
                }
            }

            // Figure out which cards in the board are absent, due to the
            // player not having voted.
            var absent_cards = $();
            for (i=0; i < old_game.board.length; i++) {
                if (card2seat[old_game.board[i]] === undefined) {
                    absent_cards = absent_cards.add('.cardstories_card_slot_' + (i + 1), element);
                }
            }

            var q = $this.create_queue(root);

            // Start by removing modal and overlay.
            $(root).queue(q, function(next) {
                var duration = 300;
                $this.animate_scale(true, 5, duration, $('.cardstories_info', element));
                next();
            });

            // Return selected card to original size.
            $(root).queue(q, function(next) {
                var card = $('.cardstories_card_slot.selected', element);
                // Create a new temporary slot just to grab the original dimensions.
                var tmp = $('<div />', {"class": card.attr("class")}).appendTo(card.parent()).show();
                var final_pos = {
                    width: tmp.width(),
                    height: tmp.height(),
                    top: tmp.position().top,
                    left: tmp.position().left
                };
                tmp.remove();
                card.animate(final_pos, 300, next);
            });

            // Now, remove any players and cards that are gone.
            if (absent_seats.length) {
                $(root).queue(q, function(next) {
                    var duration = 750;
                    absent_seats.fadeOut(duration, function() {$(this).hide();});
                    absent_cards.each(function(i) {
                        var card = $(this);
                        card.animate({
                            width: 0,
                            left: card.position().left + (card.width() / 2)
                        }, duration, function() {
                            card.hide();
                            if (i === absent_cards.length - 1) {
                                next();
                            }
                        });
                    });
                });
            }

            // Show destination element temporarily, so that positions can be calculated.
            dest_element.addClass('cardstories_active');

            var last = old_game.board.length - 1;
            var delay_next = false;
            $.each(old_game.board, function(i, value) {
                var cardq = $this.create_queue(root);
                var slot = $('.cardstories_card_slot_' + (i + 1), element);
                var sentence = $('.cardstories_sentence_box', element);

                // Insert an artificial delay for aesthetical reasons.
                if (delay_next) {
                    delay_next = false;
                    $this.delay(root, 250, q);
                }

                // Hide label.
                $('.cardstories_card_label', slot).hide();

                var dest_seat, dest_seat_pos;
                // Animate each card to the seat of the player who picked it.
                if (value === game.winner_card) {
                    delay_next = true;
                    dest_seat = $('.cardstories_picked_card', dest_element);
                    var dest_sentence = $('.cardstories_sentence_box', dest_element);

                    // Grab final positions.
                    dest_seat_pos = {
                        width: dest_seat.width(),
                        height: dest_seat.height(),
                        top: dest_seat.position().top,
                        left: dest_seat.position().left
                    };
                    var dest_sentence_pos = {
                        top: dest_sentence.position().top,
                        left: dest_sentence.position().left
                    };

                    $(root).queue(cardq, function(next) {
                        slot.animate(dest_seat_pos, 500);
                        sentence.animate(dest_sentence_pos, 500, next);
                    });
                } else if (card2seat[value] !== undefined) {
                    delay_next = true;
                    dest_seat = $('.cardstories_player_seat_card_' + card2seat[value], dest_element);

                    // Grab final position.
                    dest_seat.show();
                    dest_seat_pos = {
                        width: dest_seat.width(),
                        height: dest_seat.height(),
                        top: dest_seat.position().top,
                        left: dest_seat.position().left
                    };
                    dest_seat.hide();

                    $(root).queue(cardq, function(next) {
                        slot.animate(dest_seat_pos, 500, next);
                    });
                }

                // On the last card, animate progress bar and queue state change.
                if (i === last) {
                    $(root).queue(cardq, function(next) {
                        $this.animate_progress_bar(5, element, next);
                    });

                    $(root).queue(cardq, function(next) {
                        return $this.complete_complete(player_id, game, root);
                    });
                }

                // Queue the dequeueing of this card queue.
                $(root).queue(q, (function(cardq) {return function(next) {
                    $(root).dequeue(cardq);
                    next();
                };})(cardq));
            });

            // Hide dest_element, after all positions were calculated.
            dest_element.removeClass('cardstories_active');

            $(root).dequeue(q);
        },

        vote_anonymous: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_anonymous', root);
            this.set_active('vote_anonymous', element, root, game);
            $('.cardstories_sentence', element).text(game.sentence);
            this.display_progress_bar('player', 4, element, root);
            this.display_master_info($this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);

            // Update board state.
            this.vote_display_board(false, player_id, game, element, root);

            var deferred = $.Deferred();
            var q = $this.create_queue(root);

            if (!element.hasClass('cardstories_noop_init')) {
                element.addClass('cardstories_noop_init');

                // Display cards.
                $(root).queue(q, function(next) {
                    $this.vote_display_or_select_cards(false, null, game, element, root, next);
                });

                // Show modal.
                $(root).queue(q, function(next) {
                    var info = $('.cardstories_info', element);
                    $this.animate_scale(false, 5, 300, info, next);
                });
            }

            // Resolve deferred.
            $(root).queue(q, function(next) {
                deferred.resolve();
            });

            $(root).dequeue(q);

            return deferred;
        },

        vote_owner: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_owner', root);
            this.set_active('vote_owner', element, root, game);
            this.display_progress_bar('owner', 5, element, root);
            this.display_master_info($this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);
            $('.cardstories_sentence', element).text(game.sentence);
            var announce = $('.cardstories_results_announce', element);

            // Bind countdown select.
            $('.cardstories_countdown_select', announce).unbind('change').change(function() {
                $this.send_countdown_duration($(this).val(), player_id, game.id, root);
            });

            // Activate the announce results button if the game is ready
            // and run the countdown.
            if (game.ready) {
                // Start the countdown.
                var countdown_select = announce.find('.cardstories_countdown_select');
                $this.start_countdown(game.countdown_finish, countdown_select);
                // Enable the button.
                var b = announce.find('.cardstories_modal_button');
                b.removeClass('cardstories_button_disabled');
                b.find('span').html('ANNOUNCE RESULTS');
                b.unbind('click').click(function() {
                    $this.animate_scale(true, 5, 300, announce, function() {
                        $this.vote_owner_results_confirm(player_id, game, element, root);
                    });
                });
            }

            // Update board.
            $this.vote_display_board(true, player_id, game, element, root);

            var deferred = $.Deferred();
            var q = $this.create_queue(root);

            // Only initialize once.
            if (!element.hasClass('cardstories_noop_init')) {
                element.addClass('cardstories_noop_init');

                // Display owner's card.
                var picked_card = $('.cardstories_picked_card', element);
                var src = picked_card.metadata({type: 'attr', name: 'data'}).card.supplant({card: game.winner_card});
                picked_card.find('.cardstories_card_foreground').attr('src', src);

                // Flip owner card.
                $(root).queue(q, function(next) {
                    var front = $('.cardstories_card_template', element);
                    var back = $('.cardstories_card_6', element);
                    $this.vote_flip_card(front, back, root, next);
                });

                // Shuffle and display cards.
                $(root).queue(q, function(next) {
                    $this.vote_shuffle_cards(game, element, root, next);
                });

                // Flip the cards out.
                $(root).queue(q, function(next) {
                    $this.vote_flip_out(game, element, next);
                });

                // Display cards.
                $(root).queue(q, function(next) {
                    $this.vote_display_or_select_cards(true, game.winner_card, game, element, root, next);
                });

                // Show the announce results info box.
                $(root).queue(q, function(next) {
                    $this.animate_scale(false, 5, 300, announce, next);
                });
            }

            // Resolve deferred.
            $(root).queue(q, function(next) {
                deferred.resolve();
            });

            $(root).dequeue(q);

            return deferred;
        },

        vote_owner_results_confirm: function(player_id, game, element, root) {
            var $this = this;
            var modal = $('.cardstories_results_confirm', element);
            var overlay = $('.cardstories_modal_overlay', element);

            // Keep track of players who haven't voted yet
            var players_not_ready = 0;
            for (var i=0; i<game.players.length; i++) {
                if (game.players[i].vote === null) {
                    players_not_ready += 1;
                }
            }

            // If some players haven't picked a card, ask the GM to confirm
            if (players_not_ready > 1) { // The GM doesn't vote
                this.display_modal(modal, overlay);

                $('.cardstories_results_confirm_no', modal).unbind('click').click(function() {
                    $this.close_modal(modal, overlay, function() {
                        $this.animate_scale(false, 5, 300, $('.cardstories_results_announce', element));
                    });
                });

                $('.cardstories_results_confirm_yes', modal).unbind('click').click(function() {
                    $this.close_modal(modal, overlay, function() {
                        $this.vote_owner_results_animate(player_id, game, element, root);
                    });
                });
            } else {
                $this.vote_owner_results_animate(player_id, game, element, root);
            }
        },

        vote_owner_results_animate: function(player_id, game, element, root) {
            var $this = $.cardstories;
            var dest_element = $('.cardstories_complete', root);
            var q = $this.create_queue(root);

            // Construct picked card => seat number translation.
            var card2seat = {};
            for(var i=0, seat_nb=0; i < game.players.length; i++) {
                if (game.players[i].id != game.owner_id) {
                    seat_nb++;
                    var picked = game.players[i].picked;
                    card2seat[picked] = seat_nb;
                }
            }

            // Show destination element temporarily, so that positions can be calculated.
            dest_element.addClass('cardstories_active');

            var last = game.board.length - 1;
            $.each(game.board, function(i, value) {
                var cardq = $this.create_queue(root);
                var slot = $('.cardstories_card_slot_' + (i + 1), element);
                var sentence = $('.cardstories_sentence_box', element);

                // Insert an artificial delay for aesthetical reasons.
                if (i > 1) {
                    $this.delay(root, 150, q);
                }

                var dest_seat, dest_seat_pos;
                if (game.winner_card == value) {
                    dest_seat = $('.cardstories_picked_card', dest_element);
                    var dest_sentence = $('.cardstories_sentence_box', dest_element);

                    // Grab final positions.
                    dest_seat_pos = {
                        width: dest_seat.width(),
                        height: dest_seat.height(),
                        top: dest_seat.position().top,
                        left: dest_seat.position().left
                    };
                    var dest_sentence_pos = {
                        top: dest_sentence.position().top,
                        left: dest_sentence.position().left
                    };

                    $(root).queue(cardq, function(next) {
                        $('.cardstories_card_label', slot).fadeOut('fast');
                        slot.animate(dest_seat_pos, 500);
                        sentence.animate(dest_sentence_pos, 500, next);
                    });
                } else {
                    dest_seat = $('.cardstories_player_seat_card_' + card2seat[value], dest_element);

                    // Grab final position.
                    dest_seat.show();
                    dest_seat_pos = {
                        width: dest_seat.width(),
                        height: dest_seat.height(),
                        top: dest_seat.position().top,
                        left: dest_seat.position().left
                    };
                    dest_seat.hide();

                    $(root).queue(cardq, function(next) {
                        slot.animate(dest_seat_pos, 500, next);
                    });
                }

                if (i === last) {
                    $(root).queue(cardq, function(next) {
                        $this.animate_progress_bar(6, element, next);
                    });

                    $(root).queue(cardq, function(next) {
                        $this.send({
                            action: 'complete',
                            owner_id: player_id,
                            game_id: game.id
                        }, function() {
                            $this.game(player_id, game.id, root);
                        }, player_id, game.id, root);
                    });
                }

                // Queue the dequeueing of this card queue.
                $(root).queue(q, (function(cardq) {return function(next) {
                    $(root).dequeue(cardq);
                    next();
                };})(cardq));
            });

            // Hide dest_element, after all positions were calculated.
            dest_element.removeClass('cardstories_active');

            $(root).dequeue(q);
        },

        vote_display_board: function(setup, player_id, game, element, root) {
            var $this = this;
            var players = game.players;
            var snippets = $('.cardstories_snippets', root);
            var seat_snippet = $('.cardstories_player_seat', snippets);
            for (var i=0, seat_nb=0; i < players.length; i++) {
                if (players[i].id != game.owner_id) {
                    seat_nb++;

                    // Only initialize the seat once.
                    var seat = $('.cardstories_player_seat.cardstories_player_seat_' + seat_nb, element);
                    if (seat.children().length == 0) {
                        // Active player seat.
                        seat_snippet.clone().children().appendTo(seat);
                        var player_info = $this.get_player_info_by_id(players[i].id);
                        $this.display_player_info(player_info, seat);
                        seat.show();
                        $('.cardstories_player_arms_' + seat_nb, element).show();

                        // Only show hand cards during setup phase.
                        if (setup) {
                            // If we're a player, show the card we picked.
                            // Otherwise, just show the regular card.
                            var card = $('.cardstories_card_' + seat_nb, element);
                            if (players[i].id == player_id) {
                                var card_self = $('.cardstories_player_self_picked_card', element);
                                var foreground = $('.cardstories_card_foreground', card_self);
                                var src_template = foreground.metadata({type: 'attr', name: 'data'}).card;
                                foreground.attr('src', src_template.supplant({card: game.self[0]}));
                                card.show();
                                card_self.css({
                                    top: card.position().top,
                                    left: card.position().left,
                                    width: card.width(),
                                    height: card.height()
                                });
                                card.hide();
                                card_self.show();
                                // Mark card back for later use.
                                card.addClass('cardstories_player_self_picked_card_back');
                            } else {
                                card.show();
                            }
                        }
                    }

                    // Update player status whenever the poll returns.
                    var status = $('.cardstories_player_status', seat);
                    if (players[i].id == player_id) {
                        seat.addClass('cardstories_player_seat_self');
                        if (players[i].vote !== null) {
                            status.html('has voted!');
                        } else {
                            status.html('is voting<br />...');
                        }
                    } else {
                        if (players[i].vote !== null) {
                            seat.addClass('cardstories_player_seat_voted');
                            status.html('has voted!');
                        } else {
                            seat.addClass('cardstories_player_seat_picking');
                            status.html('is voting<br />...');
                        }
                    }
                }
            }
        },

        vote_flip_card: function(front, back, root, cb) {
            var $this = this;
            var height = front.height();
            var width = front.width();
            var top = front.position().top;
            var left = front.position().left;
            var fleft = left + (width / 2);

            var q = $this.create_queue(root);

            // Morph front out.
            $(root).queue(q, function(next) {
                front.animate({'width': 0, 'height': height, 'left': fleft}, 250, function() {
                    front.hide();
                    next();
                });
            });

            // Morph back in.
            $(root).queue(q, function(next) {
                back.css({'width': 0, 'height': height, 'top': top, 'left': fleft});
                back.show();
                back.animate({'width': width, 'height': height, 'left': left}, 250, next);
            });

            if (cb) {
                $(root).queue(q, function(next) {cb();});
            }

            $(root).dequeue(q);
        },

        vote_shuffle_cards: function(game, element, root, cb) {
            var $this = this;
            var init_duration = 750;
            var shuffle_duration = 200;
            var shuffle_times = 5;
            var shuffle_range = 120;
            var end_duration = 500;

            // Move sentence box to center.
            var sentence = $('.cardstories_sentence_box', element);
            var sentence_meta = sentence.metadata({type: 'attr', name: 'data'});
            sentence.animate({
                top: sentence_meta.ft,
                left: sentence_meta.fl
            }, init_duration);

            // Choose which cards to animate.
            var players = game.players;
            var cards = [];
            for (var i=0, slotno=0; i < players.length; i++) {
                if (players[i].id != game.owner_id) {
                    slotno++;
                    cards.push($('.cardstories_card_' + slotno, element));
                }
            }

            // Always include the owner's card.
            cards.push($('.cardstories_card_6', element));

            // A random number generator.
            var rand = function(range, negative) {
                var n = Math.floor(Math.random()*(range + 1));
                if (negative) {
                    n = n - (range/2);
                }
                return n;
            };

            // Shuffle all the cards.
            var last = cards.length - 1;
            var q = $this.create_queue(root);
            $.each(cards, function(i, card) {
                var cardno = i + 1;
                var card_slot = $('.cardstories_card_slot_' + cardno, element);
                var cardq = $this.create_queue(root);
                var card_meta = card.metadata({type: 'attr', name: 'data'});

                // Grab destination position.
                card_slot.show();
                var card_pos = {
                    width: card_slot.width(),
                    height: card_slot.height(),
                    top: card_slot.position().top,
                    left: card_slot.position().left,
                    center_top: card_meta.ct,
                    center_left: card_meta.cl
                };
                card_slot.hide();

                // Animate to center.
                $(root).queue(cardq, function(next) {
                    card.animate({
                        width: card_pos.width,
                        height: card_pos.height,
                        top: card_pos.center_top,
                        left: card_pos.center_left
                    }, init_duration, next);
                });

                // Make quick passes at animating randomly near the center.
                for (var j=0; j < shuffle_times; j++) {
                    var rt = card_pos.center_top + rand(shuffle_range, true);
                    var rl = card_pos.center_left + rand(shuffle_range, true);
                    $(root).queue(cardq, (function(rt, rl) {return function(next) {
                        card.animate({top: rt, left: rl}, shuffle_duration, 'linear', next);
                    };})(rt, rl));
                }

                // Animate to final position.
                $(root).queue(cardq, function(next) {
                    card.animate({
                        top: card_pos.top,
                        left: card_pos.left
                    }, end_duration, next);
                });

                // Pause for effect.
                $this.delay(root, 250, cardq);

                if (i === last && cb) {
                    $(root).queue(cardq, function(next) {cb();});
                }

                $(root).dequeue(cardq);
            });
        },

        vote_flip_out: function(game, element, cb) {
            var $this = this;

            // Choose which cards to animate.
            var players = game.players;
            var cards = [];
            for (var i=0, slotno=0; i < players.length; i++) {
                if (players[i].id != game.owner_id) {
                    slotno++;
                    cards.push($('.cardstories_card_' + slotno, element));
                }
            }

            // Always include the owner's card.
            cards.push($('.cardstories_card_6', element));

            // Morph each card out.
            var last = cards.length - 1;
            $.each(cards, function(i) {
                var card = $(this);
                card.animate({
                    width: 0,
                    left: card.position().left + (card.width() / 2)
                }, 500, function() {
                    card.hide();
                    if (i === last && cb) {
                        cb();
                    }
                });
            });
        },

        vote_display_or_select_cards: function(setup, picked, game, element, root, cb, ok) {
            var $this = this;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_card_slot', snippets);

            var q = $this.create_queue(root);
            var last = game.board.length - 1;
            $.each(game.board, function(i, value) {
                var cardq = $this.create_queue(root);
                var slotno = i + 1;
                var slot = $('.cardstories_card_slot_' + slotno, element);

                // Populate it.
                slot_snippet.clone().children().appendTo(slot);

                // Set the proper card.
                var card = $('.cardstories_card_foreground', slot);
                var src = card.metadata({type: 'attr', name: 'data'}).card.supplant({card: value});
                card.attr('src', src);

                // Save initial slot position.
                slot.show();
                var init_pos = {
                    width: slot.width(),
                    height: slot.height(),
                    top: slot.position().top,
                    left: slot.position().left,
                    zIndex: 0
                };

                // Animate it in during setup phase.
                if (setup) {
                    // Init pre-animation CSS.
                    slot.css({'width': 0, 'left': init_pos.left + (init_pos.width / 2)});

                    // Animate it in.
                    $(root).queue(cardq, function(next) {
                        slot.animate({'width': init_pos.width, 'left': init_pos.left}, 500, next);
                    });
                }

                // If this card was picked by the player, show the label.
                // If this card was voted for by the player, enlarge it.
                // Otherwise, if live, enable it for selection.
                if (picked === value) {
                    var label = $('.cardstories_card_label', slot);
                    // Animate label during setup phase.
                    if (setup) {
                        $(root).queue(cardq, function(next) {
                            label.fadeIn('fast', function() {
                                $(this).show(); // A workaround for http://bugs.jquery.com/ticket/8892
                                next();
                            });
                        });
                    } else {
                        label.show();
                    }
                } else {
                    var factor = 1.4;
                    var large_width = init_pos.width * factor;
                    var large_height = init_pos.height * factor;
                    var large_pos = {
                        width: large_width,
                        height: large_height,
                        top: init_pos.top - (large_height - init_pos.height)/2,
                        left: init_pos.left - (large_width - init_pos.width)/2
                    };

                    // If the player has already voted for this card, show it
                    // enlarged.  Otherwise, if a select callback was defined,
                    // enable it for selection.
                    if (game.self && game.self[1] == value) {
                        slot.addClass('selected');
                        slot.css('z-index', 1);
                        slot.css(large_pos);
                    } else if (ok) {
                        slot.addClass('live');
                        slot.unbind('click').click(function() {
                            if(!slot.hasClass('selected')) {
                                slot.addClass('selected');
                                var duration = 300;
                                slot.css('z-index', 1);
                                slot.animate(large_pos, duration);
                                // Classes don't work for this: animate_scale()
                                // screws it up.  So we resort to metadata.
                                var confirm = $('.cardstories_card_confirm', element);
                                var confirm_meta = confirm.metadata({type: 'attr', name: 'data'});
                                if (slot.hasClass('top')) {
                                    confirm.css('top', confirm_meta.bottom);
                                } else {
                                    confirm.css('top', confirm_meta.top);
                                }
                                $this.animate_scale(false, 5, duration, confirm);
                                $('.cardstories_card_confirm_ok', confirm).unbind('click').click(function() {
                                    $this.animate_scale(true, 5, duration, confirm, function() {
                                        ok(i, value);
                                    });
                                });
                                $('.cardstories_card_confirm_cancel', confirm).unbind('click').click(function() {
                                    slot.animate(init_pos, duration);
                                    $this.animate_scale(true, 5, duration, confirm, function() {
                                        slot.removeClass('selected');
                                    });
                                });
                            }
                        });
                    }
                }

                if (i === last && cb) {
                    $(root).queue(cardq, function(next) { cb(); });
                }

                $(root).dequeue(cardq);
            });
        },

        complete: function(player_id, game, root) {
            var state = $(root).data('cardstories_state');
            var deferred;
            if (state && state.dom === 'vote_voter_wait') {
                deferred = this.vote_voter_wait_to_complete(player_id, state.game, game, root);
            } else {
                deferred = this.complete_complete(player_id, game, root);
            }
            this.poll_discard(root);
            this.poll_plugin(player_id, game.id, root);

            return deferred;
        },

        complete_complete: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_complete', root);
            this.set_active('complete', element, root, game);
            this.display_master_info($this.get_master_info(game), element);
            this.init_board_buttons(player_id, element, root);
            $('.cardstories_sentence', element).text(game.sentence);

            // Display owner's card.
            var picked_card = $('.cardstories_picked_card', element);
            var src = picked_card.metadata({type: 'attr', name: 'data'}).card.supplant({card: game.winner_card});
            picked_card.find('.cardstories_card_foreground').attr('src', src);

            // Set progress bar and master seat class.
            var master_seat = $('.cardstories_master_seat', element);
            if (game.owner) {
                this.display_progress_bar('owner', 6, element, root);
                master_seat.addClass('owner');
            } else {
                this.display_progress_bar('player', 5, element, root);
                master_seat.addClass('player');
            }

            var deferred = $.Deferred();

            // Display board
            this.complete_display_board(game, element, root);

            // Only show initial animations once.
            if (!element.hasClass('cardstories_noop_init')) {
                element.addClass('cardstories_noop_init');

                var q = $this.create_queue(root);

                // Animate envelopes.
                $(root).queue(q, function(next) {
                    $this.complete_display_votes(game, element, root, next);
                });

                // Show the results box with next game info.
                $(root).queue(q, function(next) {
                    $this.complete_display_results_and_next_game(player_id, game, element, root, next);
                });

                // Resolve deferred.
                $(root).queue(q, function(next) {
                    deferred.resolve();
                    next();
                });

                $(root).dequeue(q);
            } else {
                deferred.resolve();
            }

            return deferred;
        },

        complete_display_results_and_next_game: function(player_id, game, element, root, cb) {
            var $this = this;

            // Get the player
            var player;
            for (var i=0; i < game.players.length; i++) {
                if (game.players[i].id == player_id) {
                    player = game.players[i];
                }
            }

            var q = $this.create_queue(root);

            // Only show the results/continue button if this is an active player
            // (was participating in the game, is not an anonymous viewer)
            if (player) {
                // Show results box, but only if the player voted (or the player is the GM).
                var show_results_box = player.vote !== null || game.owner;
                if (show_results_box) {
                    $(root).queue(q, function(next) {
                        $this.complete_display_results(player, game, element, root, next);
                    });
                }

                // Show next game box/button
                $(root).queue(q, function(next) {
                    $this.complete_display_next_game(!show_results_box, player_id, game, element, root, next);
                });
            }

            $(root).queue(q, function(next) {
                if (cb) {
                    cb();
                }
            });

            $(root).dequeue(q);
        },

        complete_display_board: function(game, element, root) {
            var $this = this;
            var players = game.players;
            var snippets = $('.cardstories_snippets', root);
            var seat_snippet = $('.cardstories_player_seat', snippets);
            var seatcard_snippet = $('.cardstories_card_slot', snippets);
            for (var i=0, seat_nb=0; i < players.length; i++) {
                if (players[i].id != game.owner_id) {
                    seat_nb++;

                    // Only initialize the seat once.
                    var seat = $('.cardstories_player_seat.cardstories_player_seat_' + seat_nb, element);
                    if (seat.children().length == 0) {
                        // Active player seat.
                        seat_snippet.clone().children().appendTo(seat);
                        seat.addClass('cardstories_player_seat_joined');
                        var player_info = $this.get_player_info_by_id(players[i].id);
                        $this.display_player_info(player_info, seat);
                        seat.show();
                        $('.cardstories_player_arms_' + seat_nb, element).show();

                        // Active player card, if picked.
                        if (players[i].picked) {
                            var seatcard = $('.cardstories_player_seat_card_' + seat_nb, element);

                            // Populate it.
                            seatcard_snippet.clone().children().appendTo(seatcard);

                            // Set the proper card.
                            var card = $('.cardstories_card_foreground', seatcard);
                            var src = card.metadata({type: 'attr', name: 'data'}).card.supplant({card: players[i].picked});
                            card.attr('src', src);

                            seatcard.show();
                        }

                        // Show envelope if player voted.
                        if (players[i].vote) {
                            $('.cardstories_envelope_' + seat_nb, element).show();
                        }
                    }
                }
            }
        },

        complete_display_votes: function(game, element, root, cb) {
            var $this = this;
            var players = game.players;

            // Construct picked card => slot number translation.
            var card2seat = {};
            for(var i=0, seat_nb=0; i < players.length; i++) {
                var picked = players[i].picked;
                if (players[i].id != game.owner_id) {
                    seat_nb++;
                    if (picked) {
                        card2seat[picked] = seat_nb;
                    }
                } else {
                    card2seat[picked] = 6;
                }
            }

            var snippets = $('.cardstories_snippets', root);
            var vote_slot_snippet = $('.cardstories_vote_slot', snippets);
            var q = $this.create_queue(root);

            // Insert fashionable delay.
            $this.delay(root, 400, q);

            $.each(players, function(i, player) {
                // Skip the owner.
                if (players[i].id == game.owner_id) {
                    return;
                }

                var envelope = $('.cardstories_envelope_' + i, element);
                var vote, denvelope;
                if (card2seat[player.vote] !== undefined) {
                    // Insert the vote
                    var votes = $('.cardstories_votes_' + card2seat[player.vote], element);
                    vote = vote_slot_snippet.clone();
                    vote.appendTo(votes);

                    // Get top/left coordinates of the destination
                    // envelope. Elements must be visible for position()
                    // to work.
                    var vpos = votes.position();
                    denvelope = $('.cardstories_envelope', vote);
                    denvelope.show();
                    var pos = denvelope.show().position();
                    denvelope.hide();
                    var dst_top = vpos.top + pos.top;
                    var dst_left = vpos.left + pos.left;

                    // Queue envelope animation.
                    $(root).queue(q, function(next) {
                        envelope.animate({'top': dst_top,'left': dst_left}, 500, next);
                    });
                } else {
                    $(root).queue(q, function(next) {
                        envelope.fadeOut(500, function() {
                            $(this).hide();
                            next();
                        });
                    });
                }

                // Show voter name and change seat status.
                $(root).queue(q, function(next) {
                    var seat = $('.cardstories_player_seat_' + i, element);
                    var status = $('.cardstories_player_status', seat);
                    var player_voted = player.vote !== null;

                    if (player_voted) {
                        var voter_name = $('.cardstories_voter_name', vote);
                        var player_info = $this.get_player_info_by_id(player.id);
                        voter_name.html(player_info.name + '\'s vote');
                        voter_name.fadeIn('fast', next);

                        if (player.win === 'n') {
                            seat.addClass('cardstories_player_seat_lost');
                            status.html('LOSES!');
                            if (card2seat[player.vote] !== undefined) {
                                vote.addClass('lost');
                                denvelope.show();
                                envelope.fadeOut('fast');
                            }
                        } else {
                            seat.addClass('cardstories_player_seat_won');
                            status.html('WINS!');
                        }
                    } else {
                        seat.addClass('cardstories_player_seat_no_vote');
                        status.html("DIDN'T VOTE!");
                        next();
                    }
                });
            });

            $(root).queue(q, function(next) {
                var master_seat = $('.cardstories_master_seat', element);
                var master_status = $('.cardstories_master_status', master_seat);
                if (players[0].win === 'y') {
                    master_seat.addClass('cardstories_master_seat_won');
                    master_status.html('WINS!');
                } else {
                    master_seat.addClass('cardstories_master_seat_lost');
                    master_status.html('LOSES!');
                }
                next();
            });

            $(root).queue(q, function(next) {
                if (cb) {
                    cb();
                }
            });

            $(root).dequeue(q);
        },

        complete_fade_out_results_box: function(box, element, root, cb) {
            var $this = this;
            var continue_btn = $('.cardstories_complete_continue > img', element);
            var next_game = $('.cardstories_next_game', element);

            // Stop any running levelup sounds.
            $.cardstories_audio.stop('fireworks', root);
            $.cardstories_audio.stop('applause', root);
            $.cardstories_audio.stop('bgm', root);

            // Mark the element with a cardstories_results_closed class.
            element.addClass('cardstories_results_closed');

            // Make sure to only start animating the continue button out once both,
            // the box and the next_game info have finished fading out.
            var box_deferred = $.Deferred();
            var next_game_deferred = $.Deferred();
            box.fadeOut('slow', function() {
                $(this).hide(); // A workaround for http://bugs.jquery.com/ticket/8892
                box_deferred.resolve();
            });
            next_game.fadeOut('slow', function() {
                $(this).hide(); // A workaround for http://bugs.jquery.com/ticket/8892
                next_game_deferred.resolve();
            });
            $.when(box_deferred, next_game_deferred).then(function() {
                // Animate the button out.
                $this.animate_scale(true, 5, 500, continue_btn, cb);
            });
        },

        complete_close_results_box: function(box, element, root, cb) {
            var $this = this;
            $this.complete_fade_out_results_box(box, element, root, function() {
                var continue_btn = $('.cardstories_complete_continue', element);
                continue_btn.addClass('cardstories_centered');
                var continue_img = $('> img', continue_btn);
                // Reset inline styles that might have been left over by
                // previous animations.
                continue_img.css({top: '', left: ''});
                // Animate it in.
                $this.animate_scale(false, 5, 500, continue_img, cb);
            });
        },

        complete_display_results: function(player, game, element, root, cb) {
            var $this = this;
            var box = $('.cardstories_results', element);

            // Did the owner lose?
            var owner_lost = true;
            if (game.players[0].win == 'y') {
                owner_lost = false;
            }

            // Determine why the owner lost.  If nobody voted on the
            // correct card, it was too hard.  Otherwise, it was too
            // easy.
            var too_hard = true;
            var i;
            if (owner_lost) {
                for (i=0; i < game.players.length; i++) {
                    if (game.winner_card == game.players[i].vote) {
                        too_hard = false;
                        break;
                    }
                }
            }

            // Choose explanation.
            var explanation;
            if (game.owner) {
                if (!owner_lost) {
                    explanation = $('.cardstories_won_1.cardstories_author', box);
                } else if (!too_hard) {
                    explanation = $('.cardstories_lost_1.cardstories_author', box);
                } else {
                    explanation = $('.cardstories_lost_2.cardstories_author', box);
                }
            } else if (player.vote !== null) {
                if (player.win !== 'y') {
                    explanation = $('.cardstories_lost_1.cardstories_player', box);
                } else if (!owner_lost) {
                    explanation = $('.cardstories_won_1.cardstories_player', box);
                } else if (!too_hard) {
                    explanation = $('.cardstories_won_2.cardstories_player', box);
                } else {
                    explanation = $('.cardstories_won_3.cardstories_player', box);
                }
            }

            // Choose banner, star, and sound.
            var banner;
            var star;
            var sound_id;
            if (player.win === 'y') {
                banner = $('.cardstories_results_banner_win', box);
                star = $('.cardstories_results_level_star_win', box);
                sound_id = 'score_won';
            } else {
                banner = $('.cardstories_results_banner_lose', box);
                star = $('.cardstories_results_level_star_lose', box);
                sound_id = 'score_lost';
            }

            // Only show banner if player voted.
            if (game.owner || player.vote !== null) {
                banner.show();
            }

            // Set initial score.
            var score = $('.cardstories_results_score', box);
            var html = score.html().supplant({'score': player.score_prev});
            score.html(html);

            // Bind clicks on the close button.
            $('.cardstories_results_close', box).unbind('click').click(function() {
                $this.complete_close_results_box(box, element, root);
            });

            // Animate stuff in, starting with the results box.
            var q = $this.create_queue(root);
            $(root).queue(q, function(next) {
                $this.animate_scale(false, 5, 450, box, next);
                // Start playing the "xylophone" sound.
                $.cardstories_audio.play('score_xylophone', root);
            });

            // Then fade the explanation in (if the player voted).
            if (game.owner || player.vote !== null) {
                $(root).queue(q, function(next) {
                    explanation.fadeIn('fast', next);
                });
            }

            // Wrap each character of the legend in a <span>, so we can
            // animate them individually.
            var score_legend = $('.cardstories_results_score_legend', box);
            var characters = score_legend.html().split('');
            var len = characters.length;
            for (var i = 0; i < len; i++) {
                characters[i] = '<span class="cardstories_results_score_legend_char">' + characters[i] + '</span>';
            }
            var string = characters.join('');
            score_legend.html(string);

            // Queue each character's animation.
            $.each($('.cardstories_results_score_legend_char', score_legend), function() {
                var c = $(this);
                $(root).queue(q, function(next) {
                    // All characters start at the same position.  To do so, we
                    // start by storing the character's original distance from
                    // the left border (which must be calculated because
                    // positioning is relative).
                    var left_to_parent = c.position().left;

                    // Then add the starting position class, which defines
                    // where the characters will start off, in relation to
                    // top/left of the legend container.
                    c.addClass('cardstories_results_score_legend_startpos');

                    // However, since positioning for the character is
                    // relative, we must compensate by subtracting the original
                    // distance from the left border.
                    var initial_left = parseInt(c.css('left')) - left_to_parent;
                    c.css({'left': initial_left});

                    // Store the initial 'top' value.
                    var initial_top = parseInt(c.css('top'));

                    // Now we can make the character visible, and set the
                    // initial value for "text-indent", which will be hijacked
                    // to guide the 2-dimensional animation.  This property was
                    // chosen because it has no effect on the character.
                    c.css({'visibility': 'visible', 'text-indent': 1});

                    // We animate text-indent from 1 to 0, using default
                    // easing.  This handily gives us a percentage-complete
                    // value to apply to the 2 dimensions of the animation, at
                    // each step, always ending at 0 (which in
                    // relative-positioning, is the initial position of the
                    // character).
                    c.animate({'text-indent': 0}, {duration: 300, step: function(percent_complete) {
                        // x increases linearly to 0.
                        var x = initial_left * percent_complete;

                        // y is an inverted parabola which intercepts the
                        // x-axis a little to the right of the starting left
                        // position, goes up and then comes down again to meet
                        // the x-axis at 0, the final position of the
                        // character: [y = -(x + i) * (x + j)/k], where -i and
                        // -j are the x-intercepts of the parabola, and k
                        // "flattens" it proportionately.
                        var y = -x * (x - initial_left - initial_top)/initial_left;

                        c.css({'left': x, 'top': y});
                    }});

                    next();
                });

                // Delay between characters.
                $this.delay(root, 150, q);
            });

            // Show score and play the win or lost sound
            $(root).queue(q, function(next) {
                $('.cardstories_results_score', box).fadeIn('fast', next);
                $.cardstories_audio.play(sound_id, root);
            });

            // Fashionable delay
            $this.delay(root, 400, q);

            // Did the player just level up?
            var is_levelup = player.level > player.level_prev;

            // Animate score and the level at the same time
            $(root).queue(q, function(next) {
                // Use two deferred objects to be able to run two animations concurrently,
                // and only proceed once BOTH have finished.
                var score_deferred = $.Deferred();
                var level_deferred = $.Deferred();

                // Start playing the "pinball" sound.
                $.cardstories_audio.play('score_pinball', root);
                // Animate the game score.
                var timeout = 30;
                var tmp = player.score_prev;
                function inc_score() {
                    tmp++;
                    if (tmp <= player.score) {
                        score.html(tmp);
                        $this.animationTimeout(inc_score, timeout);
                    } else {
                        score_deferred.resolve();
                    }
                }
                $this.animationTimeout(inc_score, timeout);

                var level_legend = $('.cardstories_results_level_legend', box);
                var level_legend_template = level_legend.html();
                var level_score_container = $('.cardstories_results_level_left', box);
                var level_score = $('> span', level_score_container);
                var bar = $('.cardstories_results_level_bar_front', box);

                // Function that animates the level progress bar from 0 to
                // score_left/score_next percent. The third (level) parameter
                // is the level for which the progress is being shown. This is normally
                // the current level, except when showing the level up animation.
                // The function is abstracted out order to be able to animate the level
                // bar multiple times when leveling up.
                var animate_level_bar = function(score_left, score_next, level, cb) {
                    // Set level legend.
                    var legend_html = level_legend_template.supplant({
                        level_current: level,
                        level_next: level + 1
                    });
                    level_legend.html(legend_html);
                    level_legend.show();

                    // Set initial score_next. This is actually not the correct value
                    // if the player just leveled up, but we currently don't have access
                    // to the score gap between the previous and current level, only current and next.
                    // I don't think anybody will notice this, though, so we'll just go with score_next,
                    // at least for now.
                    level_score.html(score_next);
                    level_score_container.show();

                    // The level bar and levelup info.
                    // Calculate final level bar width.
                    var percent = ((score_next - score_left) / score_next) * 100;
                    var final_width = percent + '%';

                    // Animate the level bar and level score at the same time.
                    // The duration animation would take when moving from 0 to 100%.
                    var full_duration = 2000;
                    // For animations that don't move the bar 100%, make the duration shorter.
                    // For 0% animations, the duration is half of the full duration, and for other lengths,
                    // the duration scales proprtionally. The actual numbers came from experimentation.
                    var duration = full_duration * (1 - (0.5 * score_left/score_next));

                    // Reset progress bar width.
                    bar.css('width', '');
                    var score_diff = score_next - score_left;
                    var end_sound_played = false;
                    // Start animating the bar width.
                    bar.animate({width: final_width}, {
                        duration: duration,
                        easing: 'linear',
                        // During every step of the level bar animation, also position the
                        // level score and set it's contents (counting down from entire score needed
                        // to reach the next level to the score the player still needs to get there).
                        step: function(now, fx) {
                            var score;
                            if (fx.end > 0) {
                                score = score_next - Math.round(score_diff * now/fx.end);
                            } else {
                                score = score_next;
                            }
                            level_score.html(score);
                            // Allow the score to scroll most 72% to the right
                            // (so that it doesn't scroll behind the create button and become invisible).
                            var left = Math.min(now, 72);
                            level_score_container.css('left', left + '%');

                            // Play the end (bell) sound if the bar already almost
                            // hit the end. Doing this in the complete callback is too late,
                            // because by the time the end sound is played, the bar has already
                            // started animating the second "round".
                            if (!end_sound_played && (fx.end === 0 || now/fx.end > 0.95)) {
                                end_sound_played = true;
                                $.cardstories_audio.play('score_bell', root);
                            }
                        },
                        complete: function() {
                            level_score.html(score_left);
                            if (!end_sound_played) {
                                $.cardstories_audio.play('score_bell', root);
                            }
                            if (cb) {
                                cb();
                            }
                        }
                    });
                };

                // Now start with the animation.
                // Use a seperate queue for the level animations.
                // Fade the levels in first.
                var levelq = $this.create_queue(root);
                $(root).queue(levelq, function(next) {
                    $('.cardstories_results_level_container', box).fadeIn('fast', next);
                });

                // Pop in the star.
                $(root).queue(levelq, function(next) {
                    // Scale it to its original size.
                    $this.animate_scale(false, 5, 100, star, function() {
                        // Then immediately scale it up a bit, for a nice effect.
                        $this.animate_scale(false, 0.75, 100, star, function() {
                            // Remove inline css added by animate_scale.
                            star.css({left: '', right: ''});
                            next();
                        });
                    });
                });

                // If the player leveled up, animate the bar to 100% first
                // (might need to animate it multiple times if the player advanced
                // more than one level).
                if (is_levelup) {
                    var nr_of_levels = player.level - player.level_prev;
                    for (var l = nr_of_levels; l > 0; l--) {
                        (function(l) { // Wrap the queue in a closure to capture the value of l.
                            $(root).queue(levelq, function(next) {
                                animate_level_bar(0, player.score_next, player.level - l, next);
                            });
                        })(l);
                    }
                }

                // Now run the "normal" progress bar animation to show how much
                // points left until the next level.
                $(root).queue(levelq, function(next) {
                    animate_level_bar(player.score_left, player.score_next, player.level, function() {
                        level_deferred.resolve();
                        // Stop playing the "pinball" sound.
                        $.cardstories_audio.stop('score_pinball', root);
                        next();
                    });
                });

                // Run the level animations.
                $(root).dequeue(levelq);

                // Unqueue next step of the queue after both animations have finished.
                $.when(score_deferred, level_deferred).then(next);
            });

            // Run the levelup animations if the player just leveled up.
            if (is_levelup) {
                $(root).queue(q, function(next) {
                    // Morph the banner to "Level up!".
                    var levelup_banner = $('.cardstories_results_banner_level_up', box);
                    levelup_banner.css('opacity', 0);
                    levelup_banner.show();
                    var duration = 1200;

                    // Simultaneously start fading the results banner out,
                    // and the levelup banner in. Proceed only when both animations have finished.
                    var results_deferred = $.Deferred();
                    var levelup_deferred = $.Deferred();

                    banner.animate({opacity: 0}, duration, function() {
                        $(this).hide();
                        results_deferred.resolve();
                    });
                    levelup_banner.animate({opacity: 1}, duration, function() {
                        $(this).css('opacity', '');
                        levelup_deferred.resolve();
                    });
                    $.when(results_deferred, levelup_deferred).then(next);
                });

                $(root).queue(q, function(next) {
                    // This function when invoked performs one loop of the levelup animation.
                    // One loop involves the fireworks going off and the stars fading in and out simoultaneusly.
                    // The timing is chosen so that three fadeIn/Outs of the stars take the same time as the
                    // fireworks going off first on the right, then on the left side.
                    // The loop is stopped if the element has the special cardstories_results_closed marker class.
                    var levelup_loop = function() {
                        var fireworks_deferred = $.Deferred();
                        var stars_deferred = $.Deferred();
                        var duration = 400;

                        var rising_fireworks = function(side, cb) {
                            var fireworks = $('.cardstories_results_levelup_fireworks_1_' + side, box);
                            var final_top = '-' + fireworks.height() + 'px';
                            fireworks.show();
                            fireworks.animate({top: final_top}, duration, function() {
                                fireworks.hide();
                                fireworks.css('top', ''); // clean up
                                cb();
                            });
                        };

                        var fading_fireworks = function(cb) {
                            var fireworks = $('.cardstories_results_levelup_fireworks_2', box);
                            fireworks.show();
                            fireworks.fadeOut(duration * 2, function() {
                                fireworks.hide();
                                cb();
                            });
                        };

                        var fading_stars = function(cb) {
                            var stars = $('.cardstories_results_levelup_stars', box);
                            var diff = duration / 5;
                            stars.fadeOut(diff, function() {
                                stars.fadeIn(duration*2 - diff, cb);
                            });
                        };

                        rising_fireworks('right', function() {
                            fading_fireworks(function() {
                                rising_fireworks('left', function() {
                                    fading_fireworks(function() {
                                        fireworks_deferred.resolve();
                                    });
                                });
                            });
                        });

                        fading_stars(function() {
                            fading_stars(function() {
                                fading_stars(function() {
                                    stars_deferred.resolve();
                                });
                            });
                        });

                        // Schedule another iteration of the loop, unless it should be stopped.
                        $.when(fireworks_deferred, stars_deferred).then(function() {
                            if (!element.hasClass('cardstories_results_closed') && !$this.animations_off()) {
                                levelup_loop();
                            }
                        });
                    };

                    var fireworksq = $this.create_queue(root);
                    $(root).queue(fireworksq, function(next) {
                        $.cardstories_audio.play('fireworks', root);
                        $.cardstories_audio.play('applause', root);
                        $.cardstories_audio.loop('bgm', root);
                        var stars_sprite = $('.cardstories_results_levelup_stars', box);
                        $this.animate_sprite(stars_sprite, 54, 30, false, false, next);
                    });

                    $(root).queue(fireworksq, function(next) {
                        // Start the levelup loop and then proceed immediately.
                        levelup_loop();
                        next();
                    });

                    $(root).dequeue(fireworksq);
                    next();
                });

                // Animate things off stage and kick off star loop.
                $(root).queue(q, function(next) {
                    var yay_deferred = $.Deferred();
                    var stage_deferred = $.Deferred();
                    var star_deferred = $.Deferred();

                    var yay = $('.cardstories_levelup_exclamation', box);
                    explanation.fadeOut(function() {
                        yay.fadeIn(function() {
                            yay_deferred.resolve();
                        });
                    });

                    // Star animation
                    var star_jump = $('.cardstories_results_star_jump', box);
                    var star_jump_pos = {top: parseInt(star_jump.css('top')),
                                         left: parseInt(star_jump.css('left'))};
                    // The two constants are hard-coded to compensate for the
                    // star's position in the png sequence, versus the star itself.
                    star_jump.css({top: star.offset().top - box.offset().top - 36,
                                   left: star.offset().left - box.offset().left + 2});
                    star_jump.show();
                    star.hide();
                    var duration = 400;
                    star_jump.animate(star_jump_pos, duration);
                    $this.animate_sprite(star_jump, 18, 10, false, false, function() {
                        var star_dance = $('.cardstories_results_star_dance', box);
                        star_dance.show();
                        star_jump.hide();
                        $this.animate_sprite(star_dance, 3, 4, false, true);
                        star_deferred.resolve();
                    });

                    var stageq = $this.create_queue(root);
                    $(root).queue(stageq, function(next) {
                        var stage = $('.cardstories_results_stage', box);
                        stage.animate({left: -stage.width()}, duration, function() {
                            stage.hide();
                            next();
                        });
                    });

                    var level_slot_container = $('.cardstories_results_level_slot_container', box);
                    var level_slot = $('.cardstories_results_level_slot', level_slot_container);
                    var level_slot_html = level_slot.html().supplant({
                        level_prev: player.level_prev,
                        level_cur: player.level
                    });
                    level_slot.html(level_slot_html);
                    $(root).queue(stageq, function(next) {
                        level_slot_container.fadeIn(next);
                    });

                    $(root).queue(stageq, function(next) {
                        var height = level_slot_container.height();
                        level_slot.animate({top: -height}, duration, function() {
                            stage_deferred.resolve();
                            next();
                        });
                    });

                    $(root).dequeue(stageq);

                    $.when(yay_deferred, star_deferred, stage_deferred).then(next);
                });
            }

            // Show earned cards, if any.
            if (player.earned_cards_cur) {
                var earned_card = $('.cardstories_results_earned_card', box);
                var value = player.earned_cards_cur[0];
                var src = earned_card.metadata({type: 'attr', name: 'data'}).card.supplant({card: value});
                earned_card.find('.cardstories_card_foreground').attr('src', src);

                // Fade card in.
                $(root).queue(q, function(next) {
                    earned_card.fadeIn('slow', function() {
                        earned_card.show();
                        next();
                    });
                });

                // Show squiggle.
                $(root).queue(q, function(next) {
                    $('.cardstories_results_earned_text', box).show();
                    $('.cardstories_results_squiggle', box).show();
                    next();
                });
            }

            $(root).queue(q, function(next) {
                if (cb) {
                    cb();
                }
            });

            $(root).dequeue(q);
        },

        complete_update_next_author_info: function(next_owner_id, player_id, element) {
            // Show who is going to create the next game
            if (next_owner_id === player_id) {
                $('.cardstories_next_game_author', element).css('display', 'block');
            } else {
                var next_owner_info = this.get_player_info_by_id(next_owner_id);
                if (next_owner_info !== undefined) {
                    $('.cardstories_next_author_name', element).html(next_owner_info.name);
                    $('.cardstories_next_game_player', element).css('display', 'block');
                }
            }
        },

        complete_display_next_game: function(centered, player_id, game, element, root, cb) {
            var $this = this;
            var box = $('.cardstories_next_game', element);
            var continue_button = $('.cardstories_complete_continue', element);
            var modal = $('.cardstories_modal', element);
            var overlay = $('.cardstories_modal_overlay', element);

            // If the results have been manually closed by the player,
            // the next game info should be displayed centered, regardless of what
            // the actual centered parameter passed to this function was.
            centered = centered || element.hasClass('cardstories_results_closed');

            // Readjust the positioning if displaying the centered version.
            if (centered) {
                box.addClass('cardstories_centered');
                continue_button.addClass('cardstories_centered');
            }

            var next_owner_id = $.cardstories_table.get_next_owner_id(game.id, root);
            $this.complete_update_next_author_info(next_owner_id, player_id, element);

            // Enable "continue" button
            continue_button.unbind('click').click(function() {
                continue_button.removeClass('cardstories_popped');
                // Fade out the box and animate the button out.
                var results_box = $('.cardstories_results', element);
                $this.complete_fade_out_results_box(results_box, element, root, function() {
                    // Ask the table plugin to switch to the next game as soon as possible
                    var is_ready = $.cardstories_table.on_next_game_ready(player_id, game.id, root, function(next_game_id, next_game_opts) {
                        $this.poll_discard(root);
                        $.cardstories_tabs.remove_tab_for_game(game.id, player_id, root, function() {
                            $this.reload(player_id, next_game_id, next_game_opts, root);
                        });
                    });
                    if (!is_ready) {
                        // Waiting message while the next author is creating the story
                        $this.display_modal(modal, overlay);
                    }
                });
            });

            // Reset - Called when/if the next owner changes
            $.cardstories_table.on_next_owner_change(player_id, game.id, root, function(next_owner_id) {
                $('.cardstories_next_game_author', element).css('display', 'none');
                $('.cardstories_next_game_player', element).css('display', 'none');
                var modal_visible = modal.is(':visible');

                // If the new next owner is the current player, we want him to click on the
                // "continue" button again to avoid brutally switching to a new game creation
                // without explanation.
                if (next_owner_id === player_id) {
                    var q = $this.create_queue(root);

                    if (modal_visible) {
                        $(root).queue(q, function(next) {
                            $this.close_modal(modal, overlay, next);
                        });
                    }

                    $(root).queue(q, function(next) {
                        $this.complete_display_next_game(centered || modal_visible, player_id, game, element, root);
                    });

                    $(root).dequeue(q);
                // If the next owner is not the current player simply update the next author name.
                } else {
                    $this.complete_update_next_author_info(next_owner_id, player_id, element);
                }
            });

            var q = $this.create_queue(root);

            // Pop in the continue button, if it hasn't been popped in yet.
            if (!continue_button.hasClass('cardstories_popped')) {
                $(root).queue(q, function(next) {
                    var continue_img = continue_button.find('img');
                    continue_img.css({left: '', top: ''});
                    continue_button.show();
                    continue_button.addClass('cardstories_popped');
                    $this.animate_scale(false, 5, 300, continue_img, next);
                });
            }

            // If not displaying the centered version, show the fancier animation.
            if (!centered) {
                // Slide down the next game info box
                $(root).queue(q, function(next) {
                    var final_bottom = parseInt(box.css('bottom'), 10);
                    // Set initial bottom so that the box is hidden behind the results box.
                    var initial_bottom = final_bottom + box.height();
                    // Animate it to a slightly lower position for a moment, for a nice
                    // "swinging" effect.
                    var min_bottom = 0.8 * final_bottom;
                    box.css('bottom', initial_bottom);
                    box.show();
                    // Play the "echo" sound.
                    $.cardstories_audio.play('score_echo', root);
                    box.animate({bottom: min_bottom}, 300, function() {
                        box.animate({bottom: final_bottom}, 80, next);
                    });
                });
            } else {
                // Reset the bottom if it has been fiddled with.
                // Don't show the fancy animation, because results box is not visible.
                $(root).queue(q, function(next) {
                    box.css('bottom', '');
                    $this.animate_scale(false, 5, 300, box, next);
                });
            }

            $(root).queue(q, function(next) {
                if (cb) {
                    cb();
                }
            });

            $(root).dequeue(q);
        },

        canceled: function(player_id, game, root) {
            var $this = this;
            $this.show_warning('.cardstories_game_canceled', player_id, game.id, root, function() {
                $this.reload(player_id, undefined, {force_create: true}, root);
            });
        },

        // send accepts two additional options in the "opts" argument:
        // - async: if set to false, the request will be synchronous (default true).
        // - onerror: An error handler that will be passed the error object,
        //            if the service returns an error (default $.cardstories.panic)
        send: function(query, callback, player_id, game_id, root, opts) {
            opts = opts || {};
            var $this = this;
            var onerror = opts.onerror;
            if (!onerror) {
                onerror = function(err) {
                    $this.panic(err, player_id, game_id, root);
                };
            }
            var success = function(data, status) {
                if ('error' in data) {
                    onerror(data.error);
                } else if (callback) {
                    $this.setTimeout(callback, 30);
                }
            };
            // Use an asynchronous request unless async is set to 'false' in 'opts'.
            var async = opts.async !== false;
            var options = {
                url: $this.url + '?' + $.param(query, true),
                success: success,
                async: async
            };
            return $this.ajax(options, player_id, game_id, root);
        },

        init_board_buttons: function(player_id, element, root) {
            var $this = this;

            // Start a new game
            $('.cardstories_new_story', element).unbind('click').click(function() {
                $this.reload(player_id, undefined, {force_create: true}, root);
            });
        },

        game: function(player_id, game_id, root, ajax_options) {
            var $this = this;

            var success = function(data, status) {
                // Reset table callbacks, so that they don't stick around forever.
                // If the callbacks are needed, they will be rebound by the current
                // state function.
                $.cardstories_table.on_next_owner_change(player_id, game_id, root, null);
                $.cardstories_table.on_next_game_ready(player_id, game_id, root, null);

                if ('error' in data) {
                    var error = data.error;
                    if (error.code === 'GAME_DOES_NOT_EXIST') {
                        $this.show_warning('.cardstories_game_doesnt_exist', player_id, game_id, root, function() {
                            $this.reload(player_id, undefined, {force_create: true}, root);
                        });
                    } else {
                        $this.panic(error, player_id, game_id, root);
                    }
                } else {
                    // Save greatest modification time.
                    var modified = 0;
                    for (var i=0; i < data.length; i++) {
                        if (data[i].modified && data[i].modified > modified) {
                            modified = data[i].modified;
                        }
                    }
                    if (modified && modified > 0) {
                        $(root).data('cardstories_modified', modified);
                    }

                    // Store players_info data first
                    $this.update_players_info(data, player_id, root);

                    $.each(data, function(i) {
                        var datum = this;
                        if (datum.type == 'game') {
                            $this.setTimeout(function() { $this[datum.state](player_id, datum, root); }, 30);
                        } else {
                            var plugin = $this.plugins[datum.type];
                            if (plugin && plugin.state) {
                                $this.setTimeout(function() { plugin.state(player_id, datum, root); }, 30);
                            }
                        }
                    });
                }
            };

            var request = {
                action: 'state',
                type: ['game'],
                modified: $(root).data('cardstories_modified'),
                game_id: game_id,
                player_id: player_id
            };

            // Add plugin polls.
            request = this.add_plugin_polls(request, root);

            var options = {
                url: $this.url + '?' + $.param(request, true),
                success: success
            };

            $this.ajax($.extend(options, ajax_options), player_id, game_id, root);
        },

        preload_images: function(root, cb) {
            var $this = this;
            var progress_bar = $('.cardstories_loading_bar', root);
            var progress_fill = $('.cardstories_loading_bar_fill', progress_bar);
            var preloaded_images_div = $('.cardstories_preloaded_images', root);
            var image_path = preloaded_images_div.metadata({type: 'attr', name: 'data'}).image_path;
            var loaded_count = 0;

            var images = $.map(this.images_to_preload, function(filename) {
                return {
                    src: image_path + filename,
                    img: new Image(),
                    taken: false
                };
            });

            var update_progress = function() {
                var percent = 100 * loaded_count / images.length;
                progress_fill.css('width', percent + '%');
            };

            var load_image = function(i) {
                var image = images[i];
                var is_last = i === images.length - 1;

                var onload = function() {
                    image.img.onload = image.img.onerror = null;
                    $this.setTimeout(function() {
                        loaded_count++;
                        update_progress();
                        if (!is_last) {
                            load_image(i + 1);
                        }
                        if (loaded_count === images.length) {
                            progress_bar.hide();
                            cb();
                        }
                    }, 0);
                };

                if (image.taken) {
                    // This image is already being loaded, so load the next one.
                    if (!is_last) { load_image(i + 1); }
                } else {
                    image.taken = true;
                    image.img.onload = image.img.onerror = onload;
                    image.img.src = image.src;
                    // If image is already loaded, trigger the load event manually.
                    // Some browsers will do this for us automatically, while others won't.
                    if (image.img.complete && image.img.onload) {
                        image.img.onload();
                    } else {
                        progress_bar.show();
                    }
                }
            };

            load_image(0);
            load_image(1);
            load_image(2);
        },

        images_to_preload: [
            'player_hand2dock_1.png',
            'player_hand2dock_2.png',
            'player_hand2dock_3.png',
            'player_hand2dock_4.png',
            'player_hand2dock_5.png',
            'player_join_1.png',
            'player_join_2.png',
            'player_join_3.png',
            'player_join_4.png',
            'player_join_5.png',
            'player_pick_left.png',
            'player_pick_right.png',
            'player_return_1.png',
            'player_return_2.png',
            'player_return_3.png',
            'player_return_4.png',
            'player_return_5.png',
            'complete_levelup_stars.png',
            'complete_levelup_star_jump.png',
            'complete_levelup_star_dance.png',
            'card-back.png',
            'card01.png',
            'card02.png',
            'card03.png',
            'card04.png',
            'card05.png',
            'card06.png',
            'card07.png',
            'card08.png',
            'card09.png',
            'card010.png',
            'card011.png',
            'card012.png',
            'card013.png',
            'card014.png',
            'card015.png',
            'card016.png',
            'card017.png',
            'card018.png',
            'card019.png',
            'card020.png',
            'card021.png',
            'card022.png',
            'card023.png',
            'card024.png',
            'card025.png',
            'card026.png',
            'card027.png',
            'card028.png',
            'card029.png',
            'card030.png',
            'card031.png',
            'card032.png',
            'card033.png',
            'card034.png',
            'card035.png',
            'card036.png',
            'card037.png',
            'card038.png',
            'card039.png',
            'card040.png',
            'card041.png',
            'card042.png',
            'card043.png'
        ],

        unset_active: function(root) {
            $('.cardstories_active', root).removeClass('cardstories_active');
        },

        set_active: function(dom, element, root, game) {
            var trigger = false;
            if (!$(element).hasClass('cardstories_active')) {
                trigger = true;
            }

            this.unset_active(root);
            $(element).addClass('cardstories_active');
            $(element).parents('.cardstories_root div').addClass('cardstories_active');

            // Save state
            $(root).data('cardstories_state', {game: game, dom: dom});

            // Trigger notification, but only once per dom state.
            if (trigger == true) {
                $(root).trigger('active.cardstories', [dom]);
            }
        },

        display_progress_bar: function(type, step, element, root) {
            var dst_bar = $('.cardstories_progress', element);

            // Bail out if the bar is not empty.
            if (dst_bar.children().length > 0) {
                return;
            }

            // Set dst bar type.
            dst_bar.addClass(type);

            var snippets = $('.cardstories_snippets', root);
            var src_bar = $('.cardstories_progress.' + type, snippets);

            // Clone the source bar.
            var tmp_bar = src_bar.clone();

            // Set the proper child classes.
            tmp_bar.children('.cardstories_progress_mark').addClass('cardstories_progress_mark_' + step);
            tmp_bar.children('.cardstories_step_' + step).addClass('selected');
            for (var i=1; i<step; i++) {
                tmp_bar.children('.cardstories_step_' + i).addClass('old');
            }

            // Place the children into the destination.
            tmp_bar.children().appendTo(dst_bar);

            // Finally, store current step.
            dst_bar.data('step', step);
        },

        update_players_info: function(request_data, player_id, root) {
            // Store extra information about individual players_id
            // using data found in a request answer from the webservice

            var $this = this;
            for(var i=0; i<request_data.length; i++) {
                if(request_data[i].type == 'players_info') {
                    var players_info = request_data[i];
                    for(var pid in request_data[i]) {
                        var player_info = players_info[pid];
                        $this.players_info[pid] = player_info;
                    }
                }
            }

            // Update displayed current player info.
            this.update_current_player_info(player_id, root);
        },

        get_player_info_by_id: function(player_id) {
            return this.players_info[player_id];
        },

        update_current_player_info: function(player_id, root) {
            var info_div = $('.cardstories_player_info', root);
            var player_info = this.get_player_info_by_id(player_id);
            if (player_info) {
                // If name is longer than 16 characters,
                // truncate it to first 15 characters plus three dots,
                // to not overflow the player info container.
                var name = player_info.name;
                if (name.length > 16) {
                    name = name.substr(0, 15) + '...';
                }
                $('.cardstories_name', info_div).html(name);
                $('.cardstories_level_nr', info_div).html(player_info.level);
            }
        },

        update_player_info_from_ws: function(player_id, game_id, root) {
            var $this = this;
            var deferred = $.Deferred();

            var success = function(data, status) {
                if('error' in data) {
                    $this.panic(data.error, player_id, game_id, root);
                } else {
                    $this.update_players_info(data, player_id, root);
                    deferred.resolve();
                }
            };

            var request = {
                action: 'player_info',
                player_id: player_id
            };

            $this.ajax({
                url: $this.url + '?' + $.param(request, true),
                success: success
            }, player_id, game_id, root);

            return deferred.promise();
        },

        get_master_info: function(game) {
            // Get the player_info of the game master of a provided game

            var $this = this;

            var master_id = game.owner_id;
            var master_info = $this.get_player_info_by_id(master_id);

            return master_info;
        },

        display_master_info: function(master_info, element) {
            // Display provided player_info on the game master box

            var master_name_dom = $('.cardstories_master_seat .cardstories_master_name', element);
            var master_name_dom_html = master_name_dom.html().supplant({'name': master_info.name});
            master_name_dom.html(master_name_dom_html);

            var master_avatar_dom = $('.cardstories_master_seat .cardstories_avatar', element);
            master_avatar_dom.attr('src', master_info.avatar_url);
        },

        display_player_info: function(player_info, slot) {
            // Displayer provided player_info in a player box

            $('.cardstories_player_name', slot).html(player_info.name);
            $('.cardstories_avatar', slot).attr('src', player_info.avatar_url);
        },

        display_modal: function(modal, overlay, cb_open, cb_close) {
            if (modal.is(':visible')) {
                if (cb_open) {
                    cb_open();
                }
                return;
            }

            var $this = this;
            var button = $('.cardstories_modal_button', modal);
            // Bind the close handler under a namespaced event,
            // to be able to unbind it without unbinding other click handlers.
            var evtname = 'click.closemodal';
            button.unbind(evtname).bind(evtname, function() {
                if (!$(this).hasClass('cardstories_button_disabled')) {
                    $this.close_modal(modal, overlay, cb_close);
                }
            });

            overlay.show();
            this.animate_scale(false, 5, 500, modal, cb_open);
        },

        close_modal: function(modal, overlay, cb) {
            this.animate_scale(true, 5, 500, modal, function() {
                overlay.hide();
                if (cb) {
                    cb();
                }
            });
        },

        send_countdown_duration: function(duration, player_id, game_id, root) {
            var $this = this;
            var query = {
                action: 'set_countdown',
                duration: duration,
                game_id: game_id
            };
            var ajax_opts = {
                async: false
            };
            var callback = function() {
                $this.game(player_id, game_id, root, ajax_opts);
            };
            // Use a synchronous request because this is a user-initated request,
            // and users won't be surprised by the browser blocking while waiting
            // for the response.
            $this.send(query, callback, player_id, game_id, root, ajax_opts);
        },

        start_countdown: function(end_ts, select_element) {
            var $this = this;
            // Cancel any running countdowns first.
            var meta_reset_fn = select_element.data('cardstories_countdown_reset');
            if (meta_reset_fn) { meta_reset_fn(); }

            var timeout;
            var element = select_element.find('option:selected');
            var original_html = element.html();

            // Clears any timeout and resets the html back into original state.
            var reset = function() {
                clearTimeout(timeout);
                element.html(original_html);
            };
            // Save it as metadata on the DOM element to be able to cancel
            // the countdown later.
            select_element.data('cardstories_countdown_reset', reset);

            // Returns a difference between two date/time objects, broken down into
            // days, hours, minutes and seconds.
            var timedelta = function(time1, time2) {
                var diff_secs = Math.round((time1 - time2) / 1000);
                var days = Math.floor(diff_secs / 86400);
                var hours = Math.floor((diff_secs % 86400) / 3600);
                var minutes = Math.floor((diff_secs % 3600) / 60);
                var seconds = diff_secs % 60;

                return {days: days, hours: hours, minutes: minutes, seconds: seconds};
            };

            // Returns a string representing approximate duration.
            // If duration is more than a day, returns "x days",
            // if more than an hour, returns "x hours", and so on.
            // If duration is zero return "0 seconds".
            var pprint_timedelta = function(tdelta) {
                var result;
                if (tdelta.days > 0) {
                    result = tdelta.days + ' days';
                } else if (tdelta.hours > 0) {
                    result = tdelta.hours + ' hours';
                } else if (tdelta.minutes > 0) {
                    result = tdelta.minutes + ' minutes';
                } else {
                    result = tdelta.seconds + ' seconds';
                }
                return result;
            };

            // Refreshes the contents of element with the current countdown.
            var refresh = function() {
                var now_ts = $.now();
                // Countdown will finish in diff_ms miliseconds.
                var diff_ms = end_ts - now_ts;

                // If we are already over the countdown finish deadline,
                // just print 0 seconds and stop.
                if (diff_ms < 0) {
                    element.html('0 seconds');
                } else {
                    // Round down to the nearest full second (next tick).
                    var next_tick_ms = diff_ms % 1000;
                    // Account for the fact that diff_ms may be a multiple of 1000.
                    if (next_tick_ms === 0 && diff_ms > 0) { next_tick_ms = 1000; }
                    var tdelta = timedelta(diff_ms, next_tick_ms);
                    // Display the time left.
                    element.html(pprint_timedelta(tdelta));
                    // Rinse and repeat.
                    if (next_tick_ms !== 0) {
                        timeout = $.cardstories.setTimeout(refresh, next_tick_ms);
                    }
                }
            };
            // Immediately start refreshing the countdown time.
            refresh();
        },

        email: function(game_id, root) {
            var $this = this;
            var element = $('.cardstories_subscribe', root);
            this.set_active('email', element, root);
            $(".cardstories_emailform", element).submit(function() {
                var player_id = encodeURIComponent($('.cardstories_email', element).val());
                $.cookie('CARDSTORIES_ID', player_id);
                $this.reload(player_id, game_id, {}, root);
                return true;
            });

            $('.cardstories_email', element).focus();
        },

        login: function(game_id, login_url, root) {
            if (login_url) {
                var href = login_url;
                if (game_id) {
                    href += '?game_id=' + game_id;
                }
                $.cardstories.location.href = href;
            } else {
                this.email(game_id, root);
            }
        },

        game_or_create: function(player_id, game_id, options, root) {
            if (!game_id) {
                this.create_new_game(player_id, options.previous_game_id, root);
            } else {
                this.game(player_id, game_id, root);
            }
        },

        credits: function(root) {
            var element = $('.cardstories_credits', root);
            var long = $('.cardstories_credits_long', element);
            $('.cardstories_credits_short', element).click(function() {
                long.show();
            });
            $('.cardstories_credits_close', long).click(function() {
                long.hide();
            });
            long.show(); // jScrollPane needs the element to be visible to calculate its height / width
            $('.cardstories_credits_text', long).jScrollPane({showArrows: true});
            long.hide();
        },

        load_game: function(player_id, game_id, options, root) {
            var $this = this;

            // Init modification time.
            $(root).data('cardstories_modified', 0);
            // Erase any saved state.
            $(root).data('cardstories_state', {});

            this.credits(root);

            // Notify plugins of game load.
            $.each($this.plugins, function(_, plugin) {
                if (plugin.load_game) {plugin.load_game(player_id, game_id, options, root);}
            });

            // Get player_info of the player
            // Guarantees that we'll always have this information available,
            // even when displaying a page without info from the server
            var deferred = $.when($this.update_player_info_from_ws(player_id, game_id, root)).done(function() {
                $this.game_or_create(player_id, game_id, options, root);
            });

            return deferred;
        },

        bootstrap: function(player_id, game_id, login_url, root) {
            var $this = this;
            root = $(root);
            root.addClass('cardstories_root');
            root.data('polling', false);
            root.data('dom_clone', root.html());

            if ($this.animations_off()) {
                $.fx.off = true;
            }

            $($this.window).bind('statechange', function() {
                $this.onstatechange(root);
            });

            if (!player_id) {
                player_id = parseInt($.cookie('CARDSTORIES_ID'), 10);
            }

            // Bootstrap plugins.
            $.each($this.plugins, function(_, plugin) {
                if (plugin.init) {plugin.init(player_id, game_id, root);}
            });

            $this.preload_images(root, function() {
                if (!player_id) {
                    // This should only happen when CS is used in the standalone mode
                    // In which case authentication is handled internally.
                    $this.login(game_id, login_url, root);
                } else {
                    // If game creation or a specific game aren't explicitly
                    // requested, try to join an active table/game.
                    if (!game_id && !$.cardstories.url_param('create')) {
                        $.cardstories_table.get_available_game(player_id, root, function(game_id) {
                            var opts = game_id ? {} : {force_create: true};
                            $this.reload(player_id, game_id, opts, root);
                        });
                    } else {
                        $this.load_game(player_id, game_id, {}, root);
                    }
                }
            });
        }
    };

    $.fn.cardstories = function(player_id, game_id, login_url) {
        return this.each(function() {
            $.cardstories.bootstrap(player_id, game_id, login_url, this);
        });
    };

    $.fn.trigger_keypress = function(key_code) {
        return $.event.trigger({ type : 'keypress', which : key_code });
    };
    $.fn.trigger_keydown = function(key_code) {
        return $.event.trigger({ type : 'keypress', which : key_code });
    };

    $(window).bind("beforeunload", function() {
        $.cardstories.panic = $.cardstories.noop;
    });

    // Default jQuery animation interval is 13ms. Increase it to 33ms (30 fps)
    // for better performance.
    $.fx.interval = 33;

})(jQuery);
