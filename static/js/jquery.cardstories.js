//
//     Copyright (C) 2011 Loic Dachary <loic@dachary.org>
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

    $.cardstories = {
        url: "../resource",

        SEATS: 6,

        window: window,

        location: location,

        noop: function() {},

        error: function(error) { alert(error); },

        xhr_error: function(xhr, status, error) {
            $.cardstories.error(error);
        },

        setTimeout: function(cb, delay) { return $.cardstories.window.setTimeout(cb, delay); },

        delay: function(o, delay, qname) {
            return o.delay(delay, qname);
        },

        ajax: function(o) {
            return jQuery.ajax(o);
        },

        reload: function(player_id, game_id, root) {
            var search = this.reload_link(player_id, game_id, root);
            $.cardstories.location.search = search;
        },

        permalink: function(player_id, game_id, root) {
            var search = '?';

            if(game_id !== undefined && game_id !== '') {
                search += 'game_id=' + game_id + '&';
            }
            return search;
        },

        reload_link: function(player_id, game_id, root) {
            var search = this.permalink(player_id, game_id, root);

            // Only keep the player_id in the URL if it already there (ie when it has been filled manually by the player)
            if($.query.get('player_id')) {
                search += 'player_id=' + player_id + '&';
            }
            return search;
        },

        create: function(player_id, root) {
            return this.create_pick_card(player_id, root);
        },

        create_deck: function() {
            var deck = [];
            var i;
            for(i = 1; i <= 36; i++) {
                deck.push(i);
            }
            var cards = [];
            for(i = 0; i < 7; i++) {
                cards.push(deck.splice(Math.floor(Math.random() * deck.length), 1)[0]);
            }
            return cards;
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
                            .addClass('cardstories_progress_mark' + step)
                            .appendTo(progress);
            var final_left = tmp_mark.position().left;
            tmp_mark.remove();

            // Animate the mark.
            // I fail to understand why, but tmp_mark and final_left are sometimes
            // undefined during test runs, which wracks havoc on IE8.
            if (typeof final_left !== 'undefined') {
                mark.animate({left: final_left}, 500, function() {
                    mark.removeClass('cardstories_progress_mark' + cur);
                    mark.addClass('cardstories_progress_mark' + step);
                    $('.cardstories_progress .cardstories_step' + step, element).addClass('selected');
                    for (var i=cur; i < step; i++) {
                        $('.cardstories_progress .cardstories_step' + i, element)
                            .removeClass('selected')
                            .addClass('old');
                    }
                    if (cb !== undefined) {
                        cb();
                    }
                });
            } else if (cb !== undefined) {
                cb();
            }
        },

        // For best results with animate_scale, the element must be positioned
        // absolutely, and its children must be sized and positioned relatively
        // (i.e., "em" instead of "px", percentages for widths and heights).
        animate_scale: function(reverse, factor, duration, el, cb) {
            el.show();
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
                    if (cb !== undefined) {
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

                    if (cb !== undefined) {
                        cb();
                    }
                });
            }
        },

        animate_sprite: function(movie, fps, frames, cb) {
            movie.show().sprite({
                fps: fps,
                no_of_frames: frames,
                play_frames: frames,
                oncomplete: cb
            });
        },

        create_pick_card: function(player_id, root) {
            var $this = this;
            var element = $('.cardstories_create .cardstories_pick_card', root);
            this.notify_active(root, element, 'create_pick_card');
            this.set_active(root, element);
            this.display_progress_bar(1, element, root);
            this.display_owner_nick(player_id, element);
            var deck = $this.create_deck();
            var cards = $.map(deck, function(card, index) {
                return { 'value':card };
            });

            var deferred = $.Deferred();
            var q = $({});
            var card_value, card_index;

            // Deal the cards
            q.queue('chain', function(next) {
                $this.create_pick_card_animate(cards, element, root, function() {next();});
            });

            // Set up the dock for card selection, and show the modal box.  The
            // user won't be able to select a card until "OK" is clicked.
            q.queue('chain', function(next) {
                var ok = function(_card_value, _card_index) {
                    // The selected card will be needed later in the 'chain' queue.
                    card_value = _card_value;
                    card_index = _card_index;
                    next();
                };

                $this.select_cards('create_pick_card', cards, ok, element, root).done(function() {
                    // Delay the appearance of the modal box artificially, since
                    // jqDock doesn't provide a hook for when expansion finishes.
                    $this.setTimeout(function() {
                        $this.display_modal($('.cardstories_info', element), $('.cardstories_modal_overlay', element), function() {
                            deferred.resolve();
                        });
                    }, 250);
                });

            });

            q.queue('chain', function(next) {
                $this.create_pick_card_animate_fly_to_deck(card_index, element, function() {next();});
            });
            q.queue('chain', function(next) {
                $this.animate_center_picked_card(element, card_index, card_value, function() {next();});
            });
            q.queue('chain', function(next) {
                $this.animate_progress_bar(2, element, function() {next();});
            });

            // Finally, initialize the next state.
            q.queue('chain', function(next) {
                $this.create_write_sentence(player_id, card_value, root);
            });

            q.dequeue('chain');
            return deferred;
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
                $this.create_pick_card_animate_morph_into_jqdock(cards, card_specs, element, cb);
            });
        },

        create_pick_card_animate_fly_to_board: function(cards, element, root, cb) {
            var $this = this;
            var nr_of_cards = cards.length;
            var card_fly_velocity = 1.2;   // in pixels per milisecond
            var card_delay = 100;   // delay in ms after each subsequent card starts "flying" from the deck
            var vertical_offset = 8;
            var vertical_rise_duration = 300;
            var q = $({});

            var container = $('.cardstories_cards', element);

            // Grab top.
            container.show();
            var final_top = container.position().top;
            container.hide();

            cards.each(function(i) {
                var card = $(this);
                var meta = card.metadata({type: 'attr', name: 'data'});
                var starting_top = card.position().top;
                var starting_left = card.position().left;
                var final_left = meta.final_left;
                var keyframe_top = final_top + vertical_offset;

                var fly_length = Math.sqrt(Math.pow(keyframe_top - starting_top, 2) + Math.pow(final_left - starting_left, 2));
                var fly_duration = fly_length / card_fly_velocity;

                // The first card should start flying immediately,
                // but each subsequent card should be delayed.
                if (i !== 0) {
                    $this.delay(q, card_delay, 'chain');
                }

                // The callback passed to this function should be fired
                // after the last card raises to its final position.
                var callback = (i === nr_of_cards - 1) ? cb : null;

                q.queue('chain', function(next) {
                    card.animate({top: keyframe_top, left: final_left}, fly_duration, function() {
                        card.animate({top: final_top}, vertical_rise_duration, callback);
                    });
                    next();
                });
            });

            q.dequeue('chain');
        },

        create_pick_card_animate_morph_into_jqdock: function(cards, card_specs, element, cb) {
            var nr_of_cards = cards.length;
            var card_width = cards.width();
            var src_template = $('.cardstories_card_template', element).metadata({type: 'attr', name: 'data'}).card;
            var turnaround_duration = 600;
            var q = $({});

            q.queue('chain', function(next) {
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

            q.queue('chain', function(next) {
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

            q.queue('chain', function(next) {
                cb();
                next();
            });

            q.dequeue('chain');
        },

        create_pick_card_animate_fly_to_deck: function(card_index, element, cb) {
            var $this = this;
            var deck = $('.cardstories_deck', element);
            var cards = $('.cardstories_card', deck);
            var docked_cards = $('.cardstories_cards_hand .cardstories_card', element);
            var nr_of_cards = cards.length;
            var card_fly_velocity = 1.2;   // in pixels per milisecond
            var card_delay = 100;   // delay in ms after each subsequent card starts "flying" back to the deck
            var deck_cover = $('.cardstories_deck_cover', deck);
            var final_top = deck_cover.position().top;
            var final_left = deck_cover.position().left;
            var final_width = deck_cover.width();
            var final_height = deck_cover.height();
            var deck_offset = deck.offset();
            var q = $({});

            cards.each(function(i) {
                var card = $(this);
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
                    $this.delay(q, card_delay, 'chain');
                }

                q.queue('chain', function(next) {
                    var final_props = {
                        top: final_top,
                        left: final_left,
                        width: final_width,
                        height: final_height
                    };
                    var count = 0;
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
            q.dequeue('chain');
        },

        create_write_sentence_animate_start: function(card, element, root, cb) {
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
            if (cb !== undefined) { cb('before_animation'); }

            // Animate towards the final state.
            var q = $({});
            q.queue('chain', function(next) {
                card_template.animate({
                    top: final_top,
                    left: final_left
                }, animation_duration);
                card_imgs.animate({
                    width: final_width,
                    height: final_height
                }, animation_duration, function() {next();});
            });
            q.queue('chain', function(next) {
                card_shadow.fadeIn('fast');
                write_box.fadeIn('fast', function() {
                    $(this).show(); // A workaround for http://bugs.jquery.com/ticket/8892
                    next();
                });
            });
            // If set, run the callback at the end of the queue.
            if (cb !== undefined) {
                q.queue('chain', function(next) {cb('after_animation');});
            }
            q.dequeue('chain');
        },

        create_write_sentence_animate_end: function(card, element, root, cb) {
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
            final_container.show();
            final_element.show();
            var card_top = final_card_template.position().top;
            var card_left = final_card_template.position().left;
            var card_width = final_card_template.width();
            var card_height = final_card_template.height();
            var sentence_top = final_sentence_box.position().top;
            var sentence_left = final_sentence_box.position().left;
            var sentence_width = final_sentence_box.width();
            var sentence_height = final_sentence_box.height();
            final_element.hide();
            final_container.hide();

            // Animate!
            var text = $('.cardstories_sentence', write_box).val();
            $('.cardstories_sentence', sentence_box).text(text);
            var q = $({});
            q.queue('chain', function(next) {
                write_box.fadeOut('fast');
                sentence_box.fadeIn('fast', function() {
                    $(this).show(); // A workaround for http://bugs.jquery.com/ticket/8892
                    next();
                });
            });
            q.queue('chain', function(next) {
                write_box.hide();
                sentence_box.animate({
                    top: sentence_box.position().top + 20,
                    left: sentence_box.position().left + 30,
                    width: sentence_width,
                    height: sentence_height
                }, 200, function() {next();});
            });
            q.queue('chain', function(next) {
                card_shadow.hide();
                var duration = 500;
                sentence_box.animate({
                    top: sentence_top,
                    left: sentence_left
                }, duration);
                card_template.animate({
                    top: card_top,
                    left: card_left
                }, duration);
                card_img.animate({
                    width: card_width,
                    height: card_height
                }, duration, function() {next();});
            });
            // If set, run the callback at the end of the queue.
            if (cb !== undefined) {
                q.queue('chain', function(next) {cb();});
            }
            q.dequeue('chain');
        },

        create_write_sentence: function(player_id, card, root) {
            var $this = this;
            var element = $('.cardstories_create .cardstories_write_sentence', root);
            this.notify_active(root, element, 'create_write_sentence');
            this.set_active(root, element);
            this.display_progress_bar(2, element, root);
            this.display_owner_nick(player_id, element);
            $('.cardstories_card', element).attr('class', 'cardstories_card cardstories_card' + card + ' {card:' + card + '}');
            this.create_write_sentence_animate_start(card, element, root);
            var text = $('.cardstories_sentence', element);
            var input = $('.cardstories_submit', element).hide();

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

                var success = function(data, status) {
                    if('error' in data) {
                        $this.error(data.error);
                    } else {
                        var root = $(element).parents('.cardstories_root');
                        $this.animate_progress_bar(3, element, function() {
                            $this.reload(player_id, data.game_id, root); 
                        });
                    }
                };

                $this.create_write_sentence_animate_end(card, element, root, function() {
                    var sentence = encodeURIComponent($('.cardstories_sentence', element).val());
                    var query = '?action=create';
                    query += '&owner_id=' + player_id;
                    query += '&card=' + card;
                    $this.ajax({
                        async: false,
                        timeout: 30000,
                        url: $this.url + query,
                        type: 'POST',
                        data: 'sentence=' + sentence,
                        dataType: 'json',
                        global: false,
                        success: success,
                        error: $this.xhr_error
                    });
                });
                return true;
            };
            text.val('').placeholder({ onSubmit: submit });
        },

        solo: function(player_id, root) {
            this.poll_discard(root); 
            var $this = this;
            var success = function(data, status) {
                if('error' in data) {
                    $this.error(data.error);
                } else {
                    $this.setTimeout(function() { $this.reload(player_id, data.game_id, root); }, 30);
                }
            };
            var query = '?action=solo';
            query += '&player_id=' + player_id;
            $this.ajax({
                async: false,
                timeout: 30000,
                url: $this.url + query,
                type: 'GET',
                dataType: 'json',
                global: false,
                success: success,
                error: $this.xhr_error
            });
        },

        advertise: function(owner_id, game_id, element, root) {
            var $this = this;
            var box = $('.cardstories_advertise', element);
            var overlay = $('.cardstories_owner .cardstories_modal_overlay', root);
            if (box.is(':visible')) { return; }

            var text = $.cookie('CARDSTORIES_INVITATIONS');
            var textarea = $('.cardstories_advertise_input textarea', box);
            if (text !== undefined && text !== null) {
                textarea.val(text);
            }
            textarea.placeholder();

            var background = $('.cardstories_advertise_input img', box);
            var feedback = $('.cardstories_advertise_feedback', box);
            var submit_button = $('.cardstories_send_invitation', box);

            var toggle_feedback = function(showOrHide) {
                feedback.toggle(showOrHide);
                background.toggle(!showOrHide);
                textarea.toggle(!showOrHide);
                submit_button.toggle(!showOrHide);
            };
            toggle_feedback(false);

            var is_invitation_valid = function(value) {
                var trimmed = $.trim(value);
                return trimmed && trimmed != textarea.attr('placeholder');
            };

            textarea.unbind('keyup click change').bind('keyup click change', function() {
                var val = textarea.val();
                submit_button.toggleClass('cardstories_button_disabled', !is_invitation_valid(val));
            }).change();

            submit_button.unbind('click').click(function() {
                var val = textarea.val();
                if (is_invitation_valid(val)) {
                    var invites = $.map($.grep(val.split(/\s+/), function(s,i) { return s !== ''; }),
                                        function(s,i) {
                                            return 'player_id=' + encodeURIComponent(s);
                                        });
                    $.cookie('CARDSTORIES_INVITATIONS', val);
                    $this.send_game(owner_id, game_id, element, 'action=invite&owner_id=' + owner_id + '&game_id=' + game_id + '&' + invites.join('&'));
                    toggle_feedback(true);
                    textarea.val('');

                    // Delay closing the modal a bit, so that confirmation is visible.
                    $this.setTimeout(function() {
                        $this.close_modal(box, overlay);
                    }, 700);
                }
            });

            this.display_modal(box, overlay);
        },

        poll_timeout: 300 * 1000, // must be identical to the --poll-timeout value 
                                  // server side

        poll: function(request, root) {
            var $this = this;

            if($(root).metadata().poll === undefined) {
              this.poll_ignore(request);
              return false;
            }

            $(root).metadata().poll += 1; // make sure pending polls results will be ignored
            var poll = $(root).metadata().poll;
            var success = function(answer, status) {
              if('error' in answer) {
                $this.error(answer.error);
              } else {
                if($(root).metadata().poll != poll) {
                  $this.poll_ignore(request, answer, $(root).metadata().poll, poll);
                } else {
                  if('timeout' in answer) {
                    $this.poll(request, root);
                  } else {
                    $this.game_or_lobby(request.player_id, request.game_id, root);
                  }
                }
              }
            };
            var query = '?action=poll';
            query += '&type=' + ('game_id' in request ? 'game' : 'lobby');
            query += '&modified=' + request.modified;
            if('player_id' in request) {
                query += '&player_id=' + request.player_id;
            }
            if('game_id' in request) {
                query += '&game_id=' + request.game_id;
            }
            $this.ajax({
                async: true,
                timeout: $this.poll_timeout * 2,
                url: $this.url + query,
                type: 'GET',
                dataType: 'json',
                global: false,
                success: success,
                error: $this.xhr_error
            });

            return true;
        },

        poll_ignore: function(request, answer, new_poll, old_poll) {
            if(console && console.log) {
              if(new_poll !== undefined) {
                console.log('poll ignored because ' + new_poll + ' higher than ' + old_poll);
              } else {
                console.log('poll ignored because metadata is not set');
              }
            }
        },

        poll_discard: function(root) {
            var meta = $(root).metadata();
            if(meta.poll !== undefined) {
              meta.poll += 1;
            }
            return meta.poll;
        },

        refresh_lobby: function(player_id, in_progress, my, root) {
            var $this = this;
            var success = function(data, status) {
              if('error' in data) {
                $this.error(data.error);
              } else {
                if(in_progress) {
                  $this.lobby_in_progress(player_id, data[0], root);
                } else {
                  $this.lobby_finished(player_id, data[0], root);
                }
                // FIXME not activated if the list of tables is empty ???
                $this.poll({ 'modified': data[0].modified, 'player_id': player_id }, root);
              }
            };
            var query = '?action=state';
            query += '&type=lobby';
            query += '&modified=0';
            query += '&player_id=' + player_id;
            query += '&in_progress=' + (in_progress ? 'true' : 'false');
            query += '&my=' + (my ? 'true' : 'false');
            $this.ajax({
                async: false,
                timeout: 30000,
                url: $this.url + query,
                type: 'GET',
                dataType: 'json',
                global: false,
                success: success,
                error: $this.xhr_error
            });
        },

        lobby_games: function(player_id, lobby, element, root) {
            var $this = this;
            var template = $('.cardstories_template tbody', element).html();
            var rows = [];
            for(var i = 0; i < lobby.games.length; i++) {
              var game = lobby.games[i];
              var role = game[3] == 1 ? 'cardstories_lobby_owner' : 'cardstories_lobby_player';
              var win = 'n/a';
              if(game[0] in lobby.win) {
                win = lobby.win[game[0]];
              }
              row = template.supplant({'game_id': game[0],
                                       'sentence': game[1],
                                       'state': game[2],
                                       'role': role,
                                       'win': win
                                      });
              rows.push(row);
            }
            $('.cardstories_games tbody', element).html(rows.join('\n'));
            $('.cardstories_lobby_sentence', element).click(function() {
                var game_id = $(this).metadata({type: "attr", name: "data"}).game_id;
                $this.reload(player_id, game_id, root);
              });
            if(rows.length > 0) {
              var pagesize = parseInt($('.pagesize option:selected', element).val(), 10);
              $('.cardstories_pager', element).show();
              $('table.cardstories_games', element).tablesorter().tablesorterPager({size: pagesize, positionFixed: false, container: $('.cardstories_pager', element) });
            } else {
              $('.cardstories_pager', element).hide();
            }
        },

        start_story: function(player_id, root) {
            this.poll_discard(root);
            this.create(player_id, root);
        },

        lobby_in_progress: function(player_id, lobby, root) {
            var $this = this;
            var element = $('.cardstories_lobby .cardstories_in_progress', root);
            this.notify_active(root, element, 'in_progress');
            this.set_active(root, element);
            $('.cardstories_tab_finished', element).click(function() {
                $this.refresh_lobby(player_id, false, true, root);
              });
            $('.cardstories_start_story', element).click(function() {
                $this.start_story(player_id, root);
              });
            $('.cardstories_solo', element).click(function() {
                $this.solo(player_id, root);
              });
            this.lobby_games(player_id, lobby, element, root);
        },

        lobby_finished: function(player_id, lobby, root) {
            var $this = this;
            var element = $('.cardstories_lobby .cardstories_finished', root);
            this.notify_active(root, element, 'finished');
            this.set_active(root, element);
            $('.cardstories_tab_in_progress', element).click(function() {
                $this.refresh_lobby(player_id, true, true, root);
              });
            $('.cardstories_start_story', element).click(function() {
                $this.start_story(player_id, root);
              });
            $('.cardstories_solo', element).click(function() {
                $this.solo(player_id, root);
              });
            this.lobby_games(player_id, lobby, element, root);
        },

        invitation: function(player_id, game, root) {
            var poll = true;
            var deferred;
            if(game.owner) {
                deferred = this.invitation_owner(player_id, game, root);
            } else {
                if ($.query.get('anonymous')) {
                    deferred = this.invitation_anonymous(player_id, game, root);
                } else {
                    if(game.self !== null && game.self !== undefined) {
                         if(game.self[0] === null) {
                            deferred = this.invitation_pick(player_id, game, root);
                            // do not disturb a player while (s)he is picking a card
                            poll = false;
                        } else {
                            deferred = this.invitation_pick_wait(player_id, game, root);
                        }
                    } else {
                        deferred = this.invitation_participate(player_id, game, root);
                    }
                }
            }
            if(poll) {
              this.poll({ 'modified': game.modified, 'game_id': game.id, 'player_id': player_id }, root);
            }
            return deferred;
        },

        invitation_owner: function(player_id, game, root, cb) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_owner', root);
            this.notify_active(root, element, 'invitation_owner');
            this.set_active(root, element);
            this.display_progress_bar(3, element, root);
            this.display_owner_nick(player_id, element);
            $('.cardstories_sentence', element).text(game.sentence);
            var picked_card = $('.cardstories_picked_card', element);
            var src = picked_card.metadata({type: 'attr', name: 'data'}).card.supplant({card: game.winner_card});
            picked_card.find('.cardstories_card_foreground').attr('src', src);

            // Bind go vote button, if possible.
            if (game.ready) {
                var go_vote = $('.cardstories_go_vote', element);
                $('.cardstories_modal_button', go_vote).unbind('click').click(function() {
                    $this.animate_scale(true, 5, 300, go_vote, function() {
                        $this.invitation_owner_go_vote_confirm(player_id, game, element, root);
                    });
                });
            }

            var q = $({});

            // Display the modal.
            q.queue('chain', function(next) {
                $this.invitation_owner_modal_helper($('.cardstories_info', element), $('.cardstories_modal_overlay', element), function() {next();});
            });

            // Then the invite friend buttons.
            q.queue('chain', function(next) {
                $this.invitation_owner_slots_helper($('.cardstories_invite_friend', element), player_id, game.id, element, root, function() {next();});
            });

            // Show players joining and picking cards.
            q.queue('chain', function(next) {
                $this.invitation_owner_join_helper(player_id, game, element, root, function() {
                    if (cb !== undefined) {
                        cb();
                    }
                });
            });

            q.dequeue('chain');
        },

        invitation_owner_modal_helper: function(modal, overlay, cb) {
            if (modal.hasClass('cardstories_noop')) {
                cb();
            } else {
                modal.addClass('cardstories_noop');
                this.display_modal(modal, overlay, cb);
            }
        },
 
        invitation_owner_slots_helper: function(slots, player_id, game_id, element, root, cb) {
            var $this = this;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_invite_friend', snippets);
            var last = slots.length - 1;
            slots.each(function(i) {
                var slot = $(this);

                if (slot.hasClass('cardstories_noop')) {
                    if (i === last) {
                        cb();
                    }
                } else {
                    slot.addClass('cardstories_noop');

                    // Copy over the snippet first.
                    slot_snippet.clone().children().appendTo(slot);

                    // Bind click behavior.
                    slot.unbind('click').click(function() {
                        $.cookie('CARDSTORIES_INVITATIONS', null);
                        $this.advertise(player_id, game_id, element, root);
                    });

                    // Finally animate it in.
                    $this.animate_scale(false, 5, 300, slot, function() {
                        if (i === last) {
                            cb();
                        }
                    });
                }
            });
        },

        invitation_owner_join_helper: function(player_id, game, element, root, cb) {
            var $this = this;
            var players = game.players;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_active_friend', snippets);
            var last = players.length - 1;
            var q = $({});
            var progress = $('.cardstories_progress', element);
            var go_vote = $('.cardstories_go_vote', element);
            var delay_next = false;
            for (var i=0, slotno=0, picked=0; i < players.length; i++) {
                var playerq = 'player' + i;

                // Delay this player, but only if there was at least one change
                // displayed for the previous ones.
                if (delay_next) {
                    $this.delay(q, 350, 'chain');
                    delay_next = false;
                }

                // Skip the owner.
                if (players[i][0] != game.owner_id) {
                    slotno++;

                    // Animate the progress bar as soon as one player joins.
                    // Do it in parallel with the other animations.
                    if (!progress.hasClass('cardstories_noop')) {
                        progress.addClass('cardstories_noop');
                        q.queue(playerq, function(next) {
                            $this.animate_progress_bar(4, element);
                            next();
                        });
                    }

                    // Show the go-to-vote box as soon as one player joins,
                    // also in parallel, and hide the modal, if it's visible.
                    if (!go_vote.hasClass('cardstories_noop_show')) {
                        go_vote.addClass('cardstories_noop_show');
                        var modal = $('.cardstories_info', element);
                        if (modal.css('display') == 'block') {
                            modal.find('a').click();
                        }
                        q.queue(playerq, function(next) {
                            $this.animate_scale(false, 5, 300, go_vote);
                            next();
                        });
                    }

                    // Set up the active friend slot and joining animation.
                    var slot = $('.cardstories_active_friend.cardstories_friend_slot' + slotno, element);
                    if (!slot.hasClass('cardstories_noop_join')) {
                        slot.addClass('cardstories_noop_join');
                        delay_next = true;
                        slot_snippet.clone().children().appendTo(slot);
                        slot.addClass('cardstories_active_friend_joined');
                        $('.cardstories_active_friend_name', slot).html(players[i][0]);
                        $('.cardstories_active_friend_status', slot).html('joined the game!');

                        // Queue the animation. Create a new closure to save
                        // elements for later, when dequeueing happens.
                        q.queue(playerq, (function(slot, slotno) {return function(next) {
                            var join_sprite = $('#cardstories_player_join_' + slotno);
                            $('.cardstories_invite_friend.cardstories_friend_slot' + slotno, element).fadeOut();
                            slot.show();
                            $this.animate_sprite(join_sprite, 18, 18, function() {
                                $('.cardstories_player_arms_' + slotno, element).show();
                                $('#cardstories_player_pick_' + slotno, element).show();
                                join_sprite.hide();
                                next();
                            });
                        }})(slot, slotno));

                        // Artificial delay between joining and picking.
                        $this.delay(q, 300, playerq);
                    }

                    // If the player hasn't picked a card, show the "picking"
                    // state, but only if it hasn't been shown before.  The
                    // same goes for the picked state: if a player has picked a
                    // card and the animation has been shown, don't do it
                    // again.
                    if (players[i][3] === null) {
                        if (!slot.hasClass('cardstories_noop_picking')) {
                            slot.addClass('cardstories_noop_picking');
                            delay_next = true;
                            q.queue(playerq, (function(slot) {return function(next) {
                                var status = $('.cardstories_active_friend_status', slot);
                                slot.removeClass('cardstories_active_friend_joined');
                                slot.addClass('cardstories_active_friend_picking');
                                status.addClass('cardstories_active_friend_status_picking');
                                status.html('is picking a card<br />...');
                                next();
                            }})(slot));
                        }
                    } else {
                        if (!slot.hasClass('cardstories_noop_picked')) {
                            slot.addClass('cardstories_noop_picked');
                            delay_next = true;
                            q.queue(playerq, (function(slot, slotno) {return function(next) {
                                var status = $('.cardstories_active_friend_status', slot);
                                slot.removeClass('cardstories_active_friend_joined');
                                slot.removeClass('cardstories_active_friend_picking');
                                slot.addClass('cardstories_active_friend_picked');
                                status.removeClass('cardstories_active_friend_status_picking');
                                status.addClass('cardstories_active_friend_status_picked');
                                status.html('has picked a card!');
                                var pick_sprite = $('#cardstories_player_pick_' + slotno);
                                $this.animate_sprite(pick_sprite, 18, 7, function() {
                                    pick_sprite.find('.cardstories_card').show();
                                    next();
                                });
                            }})(slot, slotno));
                        }

                        // Only visually enable the button after the second
                        // picked card animation, to match server logic.
                        picked++;
                        if (game.ready && picked == 2 && !go_vote.hasClass('cardstories_noop_enable')) {
                            go_vote.addClass('cardstories_noop_enable');
                            q.queue(playerq, function(next) {
                                b = go_vote.find('.cardstories_modal_button');
                                b.removeClass('cardstories_button_disabled');
                                b.find('span').html('GO TO VOTE');
                                next();
                            });
                        }
                    }
                }

                // If this is the last player, insert our on-complete callback.
                if (i === last) {
                    q.queue(playerq, function(next) {cb();});
                }

                // Queue the dequeueing of this player's queue. ;)
                q.queue('chain', (function(playerq) {return function(next) {
                    q.dequeue(playerq);
                    next();
                }})(playerq));
            }

            q.dequeue('chain');
        },

        invitation_owner_go_vote_confirm: function(player_id, game, element, root) {
            var $this = this;
            var modal = $('.cardstories_go_vote_confirm', element);
            var overlay = $('.cardstories_modal_overlay', element);

            this.display_modal(modal, overlay);

            $('.cardstories_go_vote_confirm_no', modal).unbind('click').click(function() {
                $this.close_modal(modal, overlay, function() {
                    $this.animate_scale(false, 5, 300, $('.cardstories_go_vote', element));
                });
            });

            $('.cardstories_go_vote_confirm_yes', modal).unbind('click').click(function() {
                $this.close_modal(modal, overlay, function() {
                    var players = game.players;
                    var nr_of_slots = players.length - 1;
                    var q = $({});
                    for (var i=0, slotno=0; i < players.length; i++) {
                        if (players[i][0] != game.owner_id) {
                            slotno++;

                            // Insert an artificial delay between players, for
                            // aesthetical reasons.
                            if (slotno > 1) {
                                $this.delay(q, 350, 'chain');
                            }

                            q.queue('chain', (function(slotno) {return function(next) {
                                $('#cardstories_player_pick_' + slotno, element).addClass('cardstories_no_background');
                                var return_sprite = $('#cardstories_player_return_' + slotno);
                                var is_last_slot = slotno === nr_of_slots;
                                $this.animate_sprite(return_sprite, 18, 18, function() {
                                    return_sprite.hide();
                                    if (is_last_slot) { next(); }
                                });
                                if (!is_last_slot) { next(); }
                            }})(slotno));
                        }
                    }

                    q.queue('chain', function(next) {
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
                            card.animate({left: final_left}, 500, cb)
                        });
                    });

                    // Queue the state change.
                    q.queue('chain', function(next) {
                        $this.send_game(player_id, game.id, element, 'action=voting&owner_id=' + player_id + '&game_id=' + game.id);
                    });

                    q.dequeue('chain');
                });
            });
        },

        invitation_pick: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick', root);
            this.notify_active(root, element, 'invitation_pick');
            this.set_active(root, element);
            this.invitation_board(player_id, game, root, element);
            var ok = function(card) {
                $this.send_game(player_id, game.id, element, 'action=pick&player_id=' + player_id + '&game_id=' + game.id + '&card=' + card);
            };
            var cards = $.map(game.self[2], function(card,index) { return {'value':card}; });
            return $this.select_cards('invitation_pick', cards, ok, element, root);
        },

        invitation_pick_wait: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick_wait', root);
            this.notify_active(root, element, 'invitation_pick_wait');
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(game.sentence);
            var card = game.self[0];
            $('.cardstories_card', element).attr('class', 'cardstories_card cardstories_wait_card' + card + ' {card:' + card + '}');
            $('.cardstories_card_change', element).unbind('click').click(function() {
                $this.invitation_pick(player_id, game, root);
            });
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
                        nudge();
                    });
                });
                $('.cardstories_card_confirm_cancel', confirm).unbind('click').click(function() {
                    $this.animate_scale(true, 5, 300, confirm, function() {
                        nudge();
                    });
                });
            };
            var hand = $('.cardstories_cards_hand', element);
            return this.display_or_select_cards(id, cards, confirm_callback, hand, root);
        },

        display_or_select_cards: function(id, cards, select_callback, element, root) {
            // In create_pick_card, jqDock needs to start collapsed, to better
            // integrate with the animation.
            var start_collapsed = id === 'create_pick_card';
            id += '_saved_element';
            var $root = $(root);
            var saved_elements = $root.data('cardstories_saved_elements') || {};
            if (saved_elements[id] === undefined) {
                saved_elements[id] = element.html();
                $root.data('cardstories_saved_elements', saved_elements);
            } else {
                element.html(saved_elements[id]);
            }
            var meta = element.metadata({type: "attr", name: "data"});
            var active_card = meta.active;
            var options = {
                'size': meta.size,
                'distance': meta.distance
            };
            if (!start_collapsed) {
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
                    if(index < cards.length && card !== null && card.value !== null) {
                        card_file = meta.card.supplant({'card': card.value});
                    }
                    var label = card && card.label ? card.label : '';
                    link.html(html.supplant({ 'label': label }));
                    var zindex = 3 * (links.length - index);
                    link.css({zIndex: zindex});
                    var background = $('.cardstories_card_background', link);
                    var has_bg = meta.card_bg && meta.card_bg.length > 0;
                    if(has_bg) {
                        background.attr('src', meta.card_bg);
                    } else if(background.attr('src') !== undefined) {
                        background.removeAttr('src');
                    }
                    background.css({zIndex: links.length - index});
                    var foreground = $('.cardstories_card_foreground', link);
                    foreground.attr('src', card_file).css({zIndex: 2 * (links.length - index)});
                    if(card) {
                        link.toggleClass('cardstories_card_inactive', card.inactive !== undefined);
                    }
                    if(select_callback !== undefined && card && card.inactive === undefined) {
                        link.metadata({type: "attr", name: "data"}).card = card.value;
                        link.unbind('click').click(function() {
                            if(!$('a.cardstories_card', element).hasClass('cardstories_card_selected')) {
                                link.addClass('cardstories_card_selected');
                                link.css({zIndex: 200});
                                var nudge = function() {
                                    link.removeClass('cardstories_card_selected');
                                    link.css({zIndex: zindex});
                                    if(has_bg) {
                                        background.attr('src', meta.card_bg);
                                    } else {
                                        background.removeAttr('src');
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

        confirm_participate: false,

        invitation_participate: function(player_id, game, root) {
            var element = $('.cardstories_invitation .cardstories_participate', root);
            if(this.confirm_participate) {
              var $this = this;
              this.notify_active(root, element, 'invitation_participate');
              this.set_active(root, element);
              $('.cardstories_sentence', element).text(game.sentence);
              $('input[type=submit]', element).click(function() {
                  $this.send_game(player_id, game.id, element, 'action=participate&player_id=' + player_id + '&game_id=' + game.id);
                });
            } else {
              this.send_game(player_id, game.id, element, 'action=participate&player_id=' + player_id + '&game_id=' + game.id);
            }
        },

        invitation_anonymous: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_invitation_anonymous', root);
            this.notify_active(root, element, 'invitation_anonymous');
            this.set_active(root, element);
            this.invitation_board(player_id, game, root, element);
        },

        invitation_board: function(player_id, game, root, element) {
            $('.cardstories_sentence', element).text(game.sentence);
            var players = game.players;
            var seat = 1;
            var i;
            for(i = 0; i < players.length; i++) {
                if(players[i][0] == game.owner_id) {
                    this.invitation_board_seat(player_id, game, root, $('.cardstories_owner_seat', element), players[i], 'owner');
                } else if(players[i][0] == player_id) {
                    this.invitation_board_seat(player_id, game, root, $('.cardstories_self_seat', element), players[i], 'self');
                } else {
                    this.invitation_board_seat(player_id, game, root, $('.cardstories_player_seat_' + seat, element), players[i], 'player');
                    seat += 1;
                }
            }
            var empty = $.cardstories.SEATS - seat;
            if(player_id !== undefined) {
                empty--;
            }
            for(i = 0; i < empty; i++, seat++) {
                $('.cardstories_player_seat_' + seat, element).addClass('cardstories_empty_seat');
            }
        },

        invitation_board_seat: function(player_id, game, root, element, player, who) {
            element.removeClass('cardstories_empty_seat');
            element.toggleClass('cardstories_player_voted', player[1] !== null);
            element.toggleClass('cardstories_player_won', player[2] != 'n');
            element.toggleClass('cardstories_player_picked', player[3] !== null);
            $('.cardstories_player_name', element).text(player[0]);
        },

        vote: function(player_id, game, root) {
            var poll = true;
            var deferred;
            if(game.owner) {
                deferred = this.vote_owner(player_id, game, root);
            } else {
                if(game.self !== null && game.self !== undefined) {
                    if(game.self[1] === null) {
                        deferred = this.vote_voter(player_id, game, root);
                        // do not disturb a voting player while (s)he is voting
                        poll = false;
                    } else {
                        deferred = this.vote_voter_wait(player_id, game, root);
                    }
                } else {
                    if ($.query.get('anonymous')) {
                        deferred = this.vote_anonymous(player_id, game, root);
                    } else {
                        deferred = this.vote_viewer(player_id, game, root);
                    }
                }
            }
            if(poll) {
                this.poll({ 'modified': game.modified, 'game_id': game.id, 'player_id': player_id }, root);
            }
            return deferred;
        },

        vote_viewer: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_viewer', root);
            this.notify_active(root, element, 'vote_viewer');
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(game.sentence);
            var cards = game.board;
            $('.cardstories_card', element).each(function(index) {
                var c = 'cardstories_card cardstories_card' + cards[index] + ' {card:' + cards[index] + '}';
                $(this).attr('class', c);
            });
        },

        vote_voter: function(player_id, game, root) {
            var element = $('.cardstories_vote .cardstories_voter', root);
            this.notify_active(root, element, 'vote_voter');
            this.set_active(root, element);
            var $this = this;
            $('.cardstories_sentence', element).text(game.sentence);
            var ok = function(card) {
                $this.send_game(player_id, game.id, element, 'action=vote&player_id=' + player_id + '&game_id=' + game.id + '&card=' + card);
            };
            var cards = [];
            var picked = game.self[0];
            var voted = game.self[1];
            var titles = [];
            for(var i = 0; i < game.board.length; i++) {
                var card = { 'value': game.board[i] };
                if(card.value == picked) {
                    card.label = 'My Card';
                    card.inactive = true;
                }
                cards.push(card);
            }
            return $this.select_cards('vote_voter', cards, ok, element, root);
        },

        vote_voter_wait: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_voter_wait', root);
            this.notify_active(root, element, 'vote_voter_wait');
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(game.sentence);
            var card = game.self[1];
            $('.cardstories_card', element).attr('class', 'cardstories_card cardstories_wait_card' + card + ' {card:' + card + '}');
            $('.cardstories_card_change', element).unbind('click').click(function() {
                $this.vote_voter(player_id, game, root);
            });
        },

        vote_anonymous: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_vote_anonymous', root);
            this.notify_active(root, element, 'vote_anonymous');
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(game.sentence);
        },

        vote_owner: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_owner', root);
            this.notify_active(root, element, 'vote_owner');
            this.set_active(root, element);
            this.display_progress_bar(5, element, root);
            this.display_owner_nick(player_id, element);
            $('.cardstories_sentence', element).text(game.sentence);

            // Display owner's card.
            var picked_card = $('.cardstories_picked_card', element);
            var src = picked_card.metadata({type: 'attr', name: 'data'}).card.supplant({card: game.winner_card});
            picked_card.find('.cardstories_card_foreground').attr('src', src);

            // Activate the announce results button if the game is ready.
            var announce = $('.cardstories_results_announce', element);
            if (game.ready) {
                b = announce.find('.cardstories_modal_button');
                b.removeClass('cardstories_button_disabled');
                b.find('span').html('ANNOUNCE RESULTS');
                b.unbind('click').click(function() {
                    $this.animate_scale(true, 5, 300, announce, function() {
                        $this.vote_owner_results_confirm(player_id, game, element, root);
                    });
                });
            }

            $this.vote_owner_display_board(game, element, root);

            // Only show initial animations once.
            if (!element.hasClass('cardstories_noop_init')) {
                element.addClass('cardstories_noop_init');
                
                var q = $({});

                // Morph owner card.
                q.queue('chain', function(next) {
                    $this.vote_owner_morph_master_card(element, next);
                });

                // Shuffle and display cards.
                q.queue('chain', function(next) {
                    $this.vote_owner_shuffle_cards(game, element, next);
                });
                
                // Display the cards.
                q.queue('chain', function(next) {
                    $this.vote_owner_display_cards(game, element, root, next);
                });

                // Show the announce results info box.
                q.queue('chain', function(next) {
                    $this.animate_scale(false, 5, 300, announce, next);
                });
                
                q.dequeue('chain');
            }
        },

        vote_owner_results_confirm: function(player_id, game, element, root) {
            var $this = this;
            var modal = $('.cardstories_results_confirm', element);
            var overlay = $('.cardstories_modal_overlay', element);

            this.display_modal(modal, overlay);

            $('.cardstories_results_confirm_no', modal).unbind('click').click(function() {
                $this.close_modal(modal, overlay, function() {
                    $this.animate_scale(false, 5, 300, $('.cardstories_results_announce', element));
                });
            });

            $('.cardstories_results_confirm_yes', modal).unbind('click').click(function() {
                var dest_element = $('.cardstories_complete', root);
                var q = $({});

                // Start by closing the modal.
                q.queue('chain', function(next) {
                    $this.close_modal(modal, overlay, next);
                });

                // Construct picked card => slot number translation.
                var card2slot = {};
                for(var i=0, slotno=0; i < game.players.length; i++) {
                    if (game.players[i][0] != game.owner_id) {
                        slotno++;
                        var picked = game.players[i][3];
                        card2slot[picked] = slotno;
                    }
                }
                
                // Show destination element temporarily, so that positions can be calculated.
                dest_element.show();

                var last = game.board.length - 1;
                for (var i=0; i < game.board.length; i++) {
                    var cardq = 'card' + i;
                    var slot = $('.cardstories_card_slot_' + (i + 1), element);

                    // Insert an artificial delay for aesthetical reasons.
                    if (i > 1) {
                        $this.delay(q, 150, 'chain');
                    }

                    if (game.winner_card == game.board[i]) {
                        var dest_slot = $('.cardstories_picked_card', dest_element);
                        var dest_sentence = $('.cardstories_sentence_box', dest_element);

                        // Grab final positions.
                        var dest_slot_pos = {
                            width: dest_slot.width(),
                            height: dest_slot.height(),
                            top: dest_slot.position().top,
                            left: dest_slot.position().left
                        };
                        var dest_sentence_pos = {
                            top: dest_sentence.position().top,
                            left: dest_sentence.position().left
                        };

                        q.queue(cardq, (function(slot, dest_slot_pos, dest_sentence_pos) { return function(next) {
                            $('.cardstories_card_label', slot).fadeOut('fast', next);
                            slot.animate({
                                'width': dest_slot_pos.width,
                                'height': dest_slot_pos.height,
                                'top': dest_slot_pos.top,
                                'left': dest_slot_pos.left
                            }, 500);
                            $('.cardstories_sentence_box', element).animate({
                                'top': dest_sentence_pos.top,
                                'left': dest_sentence_pos.left
                            }, 500, next);
                        }})(slot, dest_slot_pos, dest_sentence_pos));
                    } else {
                        var dest_slot = $('.cardstories_card_slot_' + card2slot[game.board[i]], dest_element);

                        // Grab final position.
                        dest_slot.show();
                        dest_slot_pos = {
                            width: dest_slot.width(),
                            height: dest_slot.height(),
                            top: dest_slot.position().top,
                            left: dest_slot.position().left
                        };
                        dest_slot.hide();

                        q.queue(cardq, (function(slot, dest_slot_pos) { return function(next) {
                            slot.animate({
                                'width': dest_slot_pos.width,
                                'height': dest_slot_pos.height,
                                'top': dest_slot_pos.top,
                                'left': dest_slot_pos.left
                            }, 500, next);
                        }})(slot, dest_slot_pos));
                    }

                    if (i === last) {
                        q.queue(cardq, function(next) {
                            $this.animate_progress_bar(6, element, next);
                        });

                        q.queue(cardq, function(next) {
                            $this.send_game(player_id, game.id, element, 'action=complete&owner_id=' + player_id + '&game_id=' + game.id);
                        });
                    }

                    // Queue the dequeueing of this card queue.
                    q.queue('chain', (function(cardq) {return function(next) {
                        q.dequeue(cardq);
                        next();
                    }})(cardq));
                }

                // Hide dest_element, after all positions were calculated.
                dest_element.hide();

                q.dequeue('chain');
            });
        },

        vote_owner_display_board: function(game, element, root) {
            var players = game.players;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_active_friend', snippets);
            for (var i=0, slotno=0; i < players.length; i++) {
                if (players[i][0] != game.owner_id) {
                    slotno++;

                    // Only initialize the slot once.
                    var slot = $('.cardstories_active_friend.cardstories_friend_slot' + slotno, element);
                    if (slot.children().length == 0) {
                        // Active player slot.
                        slot_snippet.clone().children().appendTo(slot);
                        $('.cardstories_active_friend_name', slot).html(players[i][0]);
                        slot.show();
                        $('.cardstories_player_arms_' + slotno, element).show();
                        
                        // Active player card, if picked.
                        if (players[i][3]) {
                            $('.cardstories_card_' + slotno, element).show();
                        }
                    }

                    // Differentiate between players who already voted,
                    // players who picked cards, and the ones who didn't.
                    var status = $('.cardstories_active_friend_status', slot);
                    if (players[i][3]) {
                        // already voted
                        if (players[i][1]) {
                            slot.addClass('cardstories_active_friend_voted');
                            status.addClass('cardstories_active_friend_status_voted');
                            status.html('has voted!');
                        } else {
                            slot.addClass('cardstories_active_friend_picking');
                            status.addClass('cardstories_active_friend_status_picking');
                            status.html('is voting<br />...');
                        }
                    } else {
                        slot.addClass('cardstories_active_friend_joined');
                        status.html('didn\'t pick');
                    }
                }
            }
        },

        vote_owner_morph_master_card: function(element, cb) {
            var card = $('.cardstories_card_6', element);
            var template = $('.cardstories_card_template', element);
            var height = template.height();
            var width = template.width();
            var top = template.position().top;
            var left = template.position().left
            var fleft = left + (width / 2);

            var q = $({});

            // Morph template out.
            q.queue('chain', function(next) {
                template.animate({'width': 0, 'height': height, 'left': fleft}, 250, function() {
                    template.hide();
                    next();
                });
            });

            // Morph card in.
            q.queue('chain', function(next) {
                card.css({'width': 0, 'height': height, 'top': top, 'left': fleft});
                card.show();
                card.animate({'width': width, 'height': height, 'left': left}, 250, next);
            });

            q.queue('chain', function(next) {
                if (cb !== undefined) {
                    cb();
                }
            });

            q.dequeue('chain');
        },

        vote_owner_shuffle_cards: function(game, element, cb) {
            var $this = this;
            var init_duration = 750;
            var shuffle_duration = 200;
            var shuffle_times = 5;
            var shuffle_range = 120;
            var end_duration = 500

            // Move sentence box to center.
            var sentence = $('.cardstories_sentence_box', element);
            var meta = sentence.metadata({type: 'attr', name: 'data'});
            var fl = meta.fl;
            var ft = meta.ft;
            sentence.animate({top: ft, left: fl}, init_duration);

            // Choose which cards to animate.
            var players = game.players;
            var cards = [];
            for (var i=0, slotno=0; i < players.length; i++) {
                if (players[i][0] != game.owner_id) {
                    slotno++;

                    // Do not include slots whose players did not pick a card.
                    if (players[i][3]) {
                        cards.push($('.cardstories_card_' + slotno, element));
                    }
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
            }

            // Shuffle all the cards.
            var last = cards.length - 1;
            var q = $({});
            for (var i=0; i < cards.length; i++) {
                var card = cards[i];
                var card_slot = $('.cardstories_card_slot_' + (i + 1), element);
                var cardq = 'card' + i;
                var meta = card.metadata({type: 'attr', name: 'data'});

                // Grab destination position.
                card_slot.show();
                var card_pos = {
                    width: card_slot.width(),
                    height: card_slot.height(),
                    top: card_slot.position().top,
                    left: card_slot.position().left,
                    center_top: meta.ct,
                    center_left: meta.cl
                };
                card_slot.hide();
                
                // Animate to center.
                q.queue(cardq, (function(card, card_pos) {return function(next) {
                    card.animate({
                        width: card_pos.width,
                        height: card_pos.height,
                        top: card_pos.center_top,
                        left: card_pos.center_left
                    }, init_duration, next);
                }})(card, card_pos));

                // Make quick passes at animating randomly near the center.
                for (var j=0; j < shuffle_times; j++) {
                    var rt = card_pos.center_top + rand(shuffle_range, true);
                    var rl = card_pos.center_left + rand(shuffle_range, true);
                    q.queue(cardq, (function(card, rt, rl) {return function(next) {
                        card.animate({top: rt, left: rl}, shuffle_duration, 'linear', next);
                    }})(card, rt, rl));
                }

                // Animate to final position.
                q.queue(cardq, (function(card, card_pos) {return function(next) {
                    card.animate({
                        top: card_pos.top,
                        left: card_pos.left
                    }, end_duration, next);
                }})(card, card_pos));

                // Pause for effect.
                $this.delay(q, 250, cardq);

                // Morph it out.
                q.queue(cardq, (function(i, card, card_pos) {return function(next) {
                    card.animate({
                        width: 0,
                        left: card_pos.left + (card_pos.width / 2)
                    }, end_duration, function() {
                        card.hide();
                        if (i === last && cb !== undefined) {
                            cb();
                        }
                        next();
                    });
                }})(i, card, card_pos));

                q.dequeue(cardq);
            }
        },

        vote_owner_display_cards: function(game, element, root, cb) {
            var $this = this;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_card_slot', snippets);
            var last = game.board.length - 1;
            var q = $({});
            for (var i=0; i < game.board.length; i++) {
                var cardq = 'card' + i;
                var slot = $('.cardstories_card_slot_' + (i + 1), element);

                // Populate it.
                slot_snippet.clone().children().appendTo(slot);
                
                // Set the proper card.
                var card = $('.cardstories_card_foreground', slot);
                var src = card.metadata({type: 'attr', name: 'data'}).card.supplant({card: game.board[i]});
                card.attr('src', src);

                // Grab pos.
                slot.show();
                var slot_pos = {
                    width: slot.width(),
                    left: slot.position().left
                };
                slot.hide();

                // Init pre-animation CSS.
                slot.css({'width': 0, 'left': slot_pos.left + (slot_pos.width / 2)});

                // Animate it in.
                q.queue(cardq, (function(i, slot, slot_pos) { return function(next) {
                    slot.show();
                    slot.animate({'width': slot_pos.width, 'left': slot_pos.left}, 500, next);
                }})(i, slot, slot_pos));

                // Show the label.
                if (game.winner_card == game.board[i]) {
                    q.queue(cardq, (function(slot) { return function(next) {
                        $('.cardstories_card_label', slot).fadeIn('fast', function() {
                            $(this).show(); // A workaround for http://bugs.jquery.com/ticket/8892
                            next();
                        });
                    }})(slot));
                }

                if (i === last && cb !== undefined) {
                    q.queue(cardq, function(next) { cb(); });
                }

                q.dequeue(cardq);
            }
        },

        complete: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_complete', root);
            this.notify_active(root, element, 'complete');
            this.set_active(root, element);
            this.display_progress_bar(6, element, root);
            this.display_owner_nick(player_id, element);
            $('.cardstories_sentence', element).text(game.sentence);

            // Display owner's card.
            var picked_card = $('.cardstories_picked_card', element);
            var src = picked_card.metadata({type: 'attr', name: 'data'}).card.supplant({card: game.winner_card});
            picked_card.find('.cardstories_card_foreground').attr('src', src);

            // Enable play again button, if owner.
            if (game.owner) {
                $('.cardstories_play_again', element).unbind('click').click(function() {
                    $('.cardstories_results', element).fadeOut('slow', function() {
                        // The players of this game will be kept since the
                        // CARDSTORIES_INVITATIONS cookie stores theirs id's.
                        $this.create(player_id, root);
                    });
                });
            } else {
                $('.cardstories_play_again', element).hide();
            }

            // Display board
            this.complete_display_board(game, element, root);
            
            // Only show initial animations once.
            if (!element.hasClass('cardstories_noop_init')) {
                element.addClass('cardstories_noop_init');
                
                var q = $({});

                // Animate envelopes.
                q.queue('chain', function(next) {
                    $this.complete_display_votes(game, element, root, next);
                });

                // Show results box.
                q.queue('chain', function(next) {
                    $this.complete_display_results(player_id, game, element, next);
                });

                q.dequeue('chain');
            }
        },

        complete_display_board: function(game, element, root) {
            var players = game.players;
            var snippets = $('.cardstories_snippets', root);
            var slot_snippet = $('.cardstories_active_friend', snippets);
            var cardslot_snippet = $('.cardstories_card_slot', snippets);
            for (var i=0, slotno=0; i < players.length; i++) {
                if (players[i][0] != game.owner_id) {
                    slotno++;

                    // Only initialize the slot once.
                    var slot = $('.cardstories_active_friend.cardstories_friend_slot' + slotno, element);
                    if (slot.children().length == 0) {
                        // Active player slot.
                        slot_snippet.clone().children().appendTo(slot);
                        slot.addClass('cardstories_active_friend_joined');
                        $('.cardstories_active_friend_name', slot).html(players[i][0]);
                        slot.show();
                        $('.cardstories_player_arms_' + slotno, element).show();

                        // Active player card, if picked.
                        if (players[i][3]) {
                            var cardslot = $('.cardstories_card_slot_' + slotno, element);

                            // Populate it.
                            cardslot_snippet.clone().children().appendTo(cardslot);
                            
                            // Set the proper card.
                            var card = $('.cardstories_card_foreground', cardslot);
                            var src = card.metadata({type: 'attr', name: 'data'}).card.supplant({card: players[i][3]});
                            card.attr('src', src);

                            cardslot.show();
                        }

                        // Show envelope if player voted.
                        if (players[i][1]) {
                            $('.cardstories_envelope_' + slotno, element).show();
                        }
                    }
                }
            }
        },

        complete_display_votes: function(game, element, root, cb) {
            var $this = this;
            var players = game.players;

            // Construct picked card => slot number translation.
            var card2slot = {};
            for(var i=0, slotno=0; i < players.length; i++) {
                var picked = players[i][3];
                if (players[i][0] != game.owner_id) {
                    slotno++;
                    if (picked) {
                        card2slot[picked] = slotno;
                    }
                } else {
                    card2slot[picked] = 6;
                }
            }
                
            var snippets = $('.cardstories_snippets', root);
            var vote_slot_snippet = $('.cardstories_vote_slot', snippets);
            var q = $({});

            // Insert fashionable delay.
            $this.delay(q, 400, 'chain');

            for (var i=0, slotno=0; i < players.length; i++) {
                if (players[i][0] != game.owner_id) {
                    slotno++;
                    var voted = players[i][1];

                    // Only include players who voted.
                    if (voted) {
                        var votes = $('.cardstories_votes_' + card2slot[voted], element);

                        // Insert the vote
                        var vote = vote_slot_snippet.clone();
                        vote.appendTo(votes);

                        // Get top/left coordinates of the destination
                        // envelope.  Elements must be visible for position()
                        // to work.
                        var vpos = votes.position();
                        var denvelope = $('.cardstories_envelope', vote);
                        denvelope.show();
                        var pos = denvelope.show().position();
                        denvelope.hide();
                        var dst_top = vpos.top + pos.top;
                        var dst_left = vpos.left + pos.left;

                        // Queue envelope animation.
                        var envelope = $('.cardstories_envelope_' + slotno, element);
                        q.queue('chain', (function(envelope, dst_top, dst_left) { return function(next) {
                            envelope.animate({'top': dst_top,'left': dst_left}, 500, next);
                        }})(envelope, dst_top, dst_left));

                        // Show voter name and change slot status.
                        var voter_name = $('.cardstories_voter_name', vote);
                        voter_name.html(players[i][0] + '\'s vote');
                        q.queue('chain', (function(i, slotno, vote, envelope, denvelope, voter_name) { return function(next) {
                            var slot = $('.cardstories_friend_slot' + slotno, element);
                            var status = $('.cardstories_active_friend_status', slot);
                            if (players[i][2] == 'n') {
                                vote.addClass('lost');
                                slot.addClass('cardstories_active_friend_lost');
                                denvelope.show();
                                envelope.fadeOut('fast');
                                status.html('LOSES!');
                            } else {
                                slot.addClass('cardstories_active_friend_won');
                                status.html('WINS!');
                            }
                            voter_name.fadeIn('fast', next);
                        }})(i, slotno, vote, envelope, denvelope, voter_name));
                    }
                }
            }

            q.queue('chain', function(next) {
                if (cb !== undefined) {
                    cb();
                }
            });

            q.dequeue('chain');
        },

        complete_display_results: function(player_id, game, element, cb) {
            // Am I a winner?
            var winner = false;
            for (var i=0; i < game.players.length; i++) {
                if (game.players[i][0] == player_id && game.players[i][2] == 'y') {
                    winner = true;
                }
            }

            var box = $('.cardstories_results', element);
            if (game.owner) {
                if (winner) {
                    $('.cardstories_won', box).show();
                } else {
                    // Determine why the owner lost.  If nobody voted on the
                    // correct card, it was too hard.  Otherwise, it was too
                    // easy.
                    var too_hard = true;
                    for (var i=0; i < game.players.length; i++) {
                        if (game.winner_card == game.players[i][1]) {
                            too_hard = false;
                            break;
                        }
                    }

                    if (too_hard) {
                        $('.cardstories_lost_2', box).show();
                    } else {
                        $('.cardstories_lost_1', box).show();
                    }
                }
            }

            box.fadeIn('slow', cb);
        },

        send_game: function(player_id, game_id, element, query) {
            var $this = this;
            var root = $(element).parents('.cardstories_root');
            var success = function(data, status) {
                if('error' in data) {
                    $this.error(data.error);
                } else {
                    $this.setTimeout(function() { $this.game(player_id, game_id, root); }, 30);
                }
            };
            var request = {
                async: false,
                timeout: 30000,
                url: $this.url + '?' + query,
                type: 'GET',
                dataType: 'json',
                global: false,
                success: success,
                error: $this.xhr_error
            };
            $this.ajax(request);
        },

        game: function(player_id, game_id, root) {
            var $this = this;

            // Activate the link to the lobby on each game
            $('.cardstories_go_lobby', root).unbind('click').click(function() {
                $this.reload(player_id);
            });

            var success = function(data, status) {
                if('error' in data) {
                    $this.error(data.error);
                } else {
                    $this[data[0].state](player_id, data[0], root);
                }
            };
            var query = '?action=state';
            query += '&type=game';
            query += '&modified=0';
            query += '&game_id=' + game_id;
            query += '&player_id=' + player_id;
            $this.ajax({
                async: false,
                timeout: 30000,
                url: $this.url + query,
                type: 'GET',
                dataType: 'json',
                global: false,
                success: success,
                error: $this.xhr_error
            });
        },

        preload_images_helper: function(root, cb) {
            var preloaded_images_div = $('.cardstories_preloaded_images', root);

            if (preloaded_images_div.hasClass('cardstories_in_progress')) {
                // ignoring...
            } else if (preloaded_images_div.hasClass('cardstories_loaded')) {
                cb();
            } else {
                this.preload_images(root, cb);
            }
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
                        // Append image to the DOM otherwise some browsers won't cache it.
                        $('<img/>').attr('src', image.src).appendTo(preloaded_images_div);
                        if (is_last) {
                            progress_bar.hide();
                            preloaded_images_div.addClass('cardstories_loaded').removeClass('cardstories_in_progress');
                            cb();
                        } else {
                            load_image(i + 1);
                        }
                    }, 1);
                };

                if (image.taken) {
                    // This image is already being loaded, so load the next one.
                    if (!is_last) { load_image(i + 1); }
                } else {
                    image.taken = true;
                    image.img.onload = image.onerror = onload;
                    image.img.src = image.src;
                    // If image is already loaded, trigger the load event manually.
                    // Some browsers will do this for us automatically, while others won't.
                    if (image.img.complete) {
                        $this.setTimeout(function() {
                            if (image.img.onload) {
                                image.img.onload();
                            }
                        }, 1);
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
            'card036.png'
        ],

        unset_active: function(root) {
            $('.cardstories_active', root).removeClass('cardstories_active');
        },

        set_active: function(root, element) { 
            this.unset_active(root);
            $(element).addClass('cardstories_active');
            $(element).parents('.cardstories_root div').addClass('cardstories_active');
        },

        notify_active: function(root, element, skin) {
            // Only trigger the event once per active element.
            if (!$(element).hasClass('cardstories_active')) {
                $(root).trigger('active.cardstories', [skin]);
            }
        },

        display_progress_bar: function(step, element, root) {
            var dst_bar = $('.cardstories_progress', element);

            // Bail out if the bar is not empty.
            if (dst_bar.children().length > 0) {
                return;
            }

            var snippets = $('.cardstories_snippets', root);
            var src_bar = $('.cardstories_progress', snippets);

            // Clone the source bar.
            var tmp_bar = src_bar.clone();

            // Set the proper classes.
            tmp_bar.children('.cardstories_progress_mark').addClass('cardstories_progress_mark' + step);
            tmp_bar.children('.cardstories_step' + step).addClass('selected');
            for (var i=1; i<step; i++) {
                tmp_bar.children('.cardstories_step' + i).addClass('old');
            }

            // Place the children into the destination.
            tmp_bar.children().appendTo(dst_bar);
            
            // Finally, store current step.
            dst_bar.data('step', step);
        },

        display_owner_nick: function(name, element) {
            var nickname = $('.cardstories_owner_seat .cardstories_nickname', element);
            var html = nickname.html();
            nickname.html(html.supplant({'nick': name}));
        },

        display_modal: function(modal, overlay, cb) {
            if (modal.is(':visible')) {
                if (cb !== undefined) {
                    cb();
                }
                return;
            }

            var $this = this;
            var button = $('.cardstories_modal_button', modal);
            button.one('click', function() {
                if (!$(this).hasClass('cardstories_button_disabled')) {
                    $this.close_modal(modal, overlay);
                }
            });

            overlay.show();
            this.animate_scale(false, 5, 500, modal, function () {
                if (cb !== undefined) {
                    cb();
                }
            });
        },

        close_modal: function(modal, overlay, cb) {
            this.animate_scale(true, 5, 500, modal, function() {
                overlay.hide();
                if (cb !== undefined) {
                    cb();
                }
            });
        },

        email: function(game_id, root) {
            var $this = this;
            var element = $('.cardstories_subscribe', root);
            this.notify_active(root, element, 'email');
            this.set_active(root, element);
            validator = $(".cardstories_emailform", element).submit(function() {
                var player_id = encodeURIComponent($('.cardstories_email', element).val());
                $.cookie('CARDSTORIES_ID', player_id);
                $this.game_or_lobby(player_id, game_id, root);
                return true;
            });

            $('.cardstories_email', element).focus();
        },

        login: function(welcome_url, game_id, root) {
            if(welcome_url !== undefined && welcome_url !== null && welcome_url !== '') {
                var href = welcome_url;
                if (game_id) {
                    href += '?game_id=' + game_id;
                }
                $.cardstories.location.href = href;
            } else {
                this.email(game_id, root);
            }
        },

        bootstrap: function(player_id, game_id, root) {
            this.credits(root);
            if(player_id === undefined || player_id === null || player_id === '') {
                player_id = $.cookie('CARDSTORIES_ID');
            }
            if(player_id === undefined || player_id === null || player_id === '') {
                this.login($.cookie('CARDSTORIES_WELCOME'), game_id, root);
            } else {
                this.game_or_lobby(player_id, game_id, root);
            }
        },

        game_or_lobby: function(player_id, game_id, root) {
            var $this = this;
            this.preload_images_helper(root, function() {
                if (game_id === undefined || game_id === '') {
                    $this.refresh_lobby(player_id, true, true, root);
                } else {
                    $this.game(player_id, game_id, root);
                }
            });
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
        }

    };

    $.fn.cardstories = function(player_id, game_id) {
        if(player_id === undefined || player_id === '') {
          player_id = $.cookie('CARDSTORIES_ID');
        }
        return this.each(function() {
            $(this).toggleClass('cardstories_root', true);
            $(this).metadata().poll = 1;
            $.cardstories.bootstrap(player_id, game_id, this);
            return this;
        });
    };

    $.fn.trigger_keypress = function(key_code) {
        return $.event.trigger({ type : 'keypress', which : key_code });
    };
    $.fn.trigger_keydown = function(key_code) {
        return $.event.trigger({ type : 'keypress', which : key_code });
    };

    $(window).bind("beforeunload", function() {
        $.cardstories.error = $.cardstories.noop;
    });

})(jQuery);
