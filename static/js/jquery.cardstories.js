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

        setInterval: function(cb, delay) { return $.cardstories.window.setInterval(cb, delay); },

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

        create_pick_card: function(player_id, root) {
            var $this = this;
            var element = $('.cardstories_create .cardstories_pick_card', root);
            this.set_active(root, element);
            this.notify_active(root, 'create_pick_card');
            var ok = function(card) {
                $this.create_write_sentence(player_id, card, root);
            };
            var deck = $this.create_deck();
            var cards = $.map(deck, function(card, index) {
                return { 'value':card };
            });

            var deferred = $.Deferred();
            $this.create_pick_card_animate(cards, element, root, function() {
                $this.select_cards('create_pick_card', cards, ok, element).done(function() {
                    // The cards that are animated to the board need to be hidden when jqDock
                    // is done initializing, otherwise they would show on top of jqDock in IE7,
                    // due to IE7's z-index bug.
                    // It would be better if this could be done inside create_pick_card_animate,
                    // but I wasn't able to find a pretty way to do it.
                    $('.cardstories_deck .cardstories_card', element).hide();
                    deferred.resolve();
                });
            });
            return deferred;
        },

        create_pick_card_animate: function(card_specs, element, root, cb) {
            var $this = this;
            var cards = $('.cardstories_deck .cardstories_card', element);

            $this.create_pick_card_animate_fly_to_board(cards, element, root, function() {
                $this.create_pick_card_animate_morph_into_jqdock(cards, card_specs, element, cb);
            });
        },

        create_pick_card_animate_fly_to_board: function(cards, element, root, cb) {
            var nr_of_cards = cards.length;
            var card_fly_velocity = 1.2;   // in pixels per milisecond
            var card_delay = 100;   // delay in ms after each subsequent card starts "flying" from the deck
            var vertical_offset = 8;
            var vertical_rise_duration = 300;
            var final_top = parseInt($('.cardstories_cards', element).css('top'), 10);
            var q = $({});

            cards.each(function(i) {
                var card = $(this);
                var meta = card.metadata({type: 'attr', name: 'data'});
                var starting_top = parseInt(card.css('top'), 10);
                var starting_left = parseInt(card.css('left'), 10);
                var final_left = meta.final_left;
                var keyframe_top = final_top + vertical_offset;

                var fly_length = Math.sqrt(Math.pow(keyframe_top - starting_top, 2) + Math.pow(final_left - starting_left, 2));
                var fly_duration = fly_length / card_fly_velocity;

                // The first card should start flying immediately,
                // but each subsequent card should be delayed.
                if (i !== 0) {
                    q.delay(card_delay, 'chain');
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
                        // one image, and the pain of working around this jqDock limitation wouldn't worth it, IMHO.
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

        create_write_sentence_animate_start: function(card, element, root, cb) {
            var write_box = $('.cardstories_write', element);
            var card_shadow = $('.cardstories_card_shadow', element);
            var card_template = $('.cardstories_card_template', element);
            var card_imgs = $('img', card_template);
            var card_foreground = card_imgs.filter('.cardstories_card_foreground');

            // Set the card's src attribute first.
            var src = card_template.metadata({type: 'attr', name: 'data'}).card.supplant({card: card});
            card_foreground.attr('src', src);

            var final_top = parseInt(card_template.css('top'), 10); // assuming the top value is given in pixels
            var final_left = parseInt(card_template.css('left'), 10); // assuming value in pixels
            var final_width = card_imgs.width();
            var final_height = card_imgs.height();
            var starting_width = 220;
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
                write_box.fadeIn('fast', function() {next();});
            });
            // If set, run the callback at the end of the queue.
            if (cb !== undefined) {
                q.queue('chain', function(next) {cb();});
            }
            q.dequeue('chain');
        },

        create_write_sentence_animate_end: function(card, element, root, cb) {
            var card_template = $('.cardstories_card_template', element);
            var card_img = $('img', card_template);
            var card_shadow = $('.cardstories_card_shadow', element);
            var final_element = $('.cardstories_invitation .cardstories_owner', root);
            var final_card_template = $('.cardstories_card_template', final_element);
            var write_box = $('.cardstories_write', element);
            var sentence_box = $('.cardstories_sentence_box', element);
            var final_sentence_box = $('.cardstories_sentence_box', final_element);

            // Calculate final position and dimensions.
            var card_top = parseInt(final_card_template.css('top'), 10);
            var card_left = parseInt(final_card_template.css('left'), 10);
            var card_width = parseInt(final_card_template.css('width'), 10);
            var card_height = parseInt(final_card_template.css('height'), 10);
            var sentence_top = parseInt(final_sentence_box.css('top'), 10);
            var sentence_left = parseInt(final_sentence_box.css('left'), 10);
            var sentence_width = parseInt(final_sentence_box.css('width'), 10);
            var sentence_height = parseInt(final_sentence_box.css('height'), 10);

            // Animate!
            var text = $('.cardstories_sentence', write_box).val();
            $('.cardstories_sentence', sentence_box).text(text);
            var q = $({});
            q.queue('chain', function(next) {
                write_box.fadeOut('fast');
                sentence_box.fadeIn('fast', function() {next();});
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
            this.set_active(root, element);
            this.notify_active(root, 'create_write_sentence');
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
                var animation_done = false;
                $this.create_write_sentence_animate_end(card, element, root, function() {
                    animation_done = true;
                });
                var success = function(data, status) {
                    if('error' in data) {
                        $this.error(data.error);
                    } else {
                        var root = $(element).parents('.cardstories_root');
                        var interval = $this.setInterval(function() {
                            if (animation_done) {
                                $this.reload(player_id, data.game_id, root); 
                                clearInterval(interval);
                            }
                        }, 250);
                    }
                };
                var sentence = encodeURIComponent($('.cardstories_sentence', element).val());
                $this.ajax({
                    async: false,
                    timeout: 30000,
                    url: $this.url + '?action=create&owner_id=' + player_id + '&card=' + card,
                    type: 'POST',
                    data: 'sentence=' + sentence,
                    dataType: 'json',
                    global: false,
                    success: success,
                    error: $this.xhr_error
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
            $this.ajax({
                async: false,
                timeout: 30000,
                url: $this.url + '?action=solo&player_id=' + player_id,
                type: 'GET',
                dataType: 'json',
                global: false,
                success: success,
                error: $this.xhr_error
            });
        },

        advertise: function(owner_id, game_id, root) {
            var $this = this;
            var element = $('.cardstories_advertise', root);
            this.set_active(root, element);
            this.notify_active(root, 'advertise');
            var text = $.cookie('CARDSTORIES_INVITATIONS');
            if(text !== undefined && text !== null) {
                $('.cardstories_text', element).text(text);
            }
            var load_text = function ($o) {
                if ($.trim($o.val()).length !== 0) {
                    $('.cardstories_submit').addClass('cardstories_submit_ready');
                    $('.cardstories_submit', element).unbind('click').click(function() {
                        var text = $('.cardstories_text', element).val();
                        var invites = $.map($.grep(text.split(/\s+/), function(s,i) { return s !== ''; }),
                                            function(s,i) {
                                                return 'player_id=' + encodeURIComponent(s);
                                            });
                        $.cookie('CARDSTORIES_INVITATIONS', text);
                        $this.send_game(owner_id, game_id, element, 'action=invite&owner_id=' + owner_id + '&game_id=' + game_id + '&' + invites.join('&'));
                      });
                } else {
                    $('.cardstories_submit', element).unbind('click');
                    $('.cardstories_submit').removeClass('cardstories_submit_ready');
                }
            };
            load_text($('.cardstories_text', element));
            $('.cardstories_text', element).unbind('keyup').keyup(function () {
                load_text($(this));
            });
            var facebookUrl = $('#facebook_url').html().supplant({'GAME_URL': escape(this.permalink(owner_id, game_id, root))});
            $('.cardstories_fb_invite', element).attr('src', facebookUrl);
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
            var query = 'modified=' + request.modified;
            var type;
            if('player_id' in request) {
              query += '&player_id=' + request.player_id;
              type = 'lobby';
            }
            if('game_id' in request) {
              query += '&game_id=' + request.game_id;
              type = 'game';
            }
            $this.ajax({
              async: true,
                  timeout: $this.poll_timeout * 2,
                  url: $this.url + '?action=poll&type=' + type + '&' + query,
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
            var query_in_progress;
            if(in_progress) {
              query_in_progress = 'true';
            } else {
              query_in_progress = 'false';
            }
            if(my) {
              my = 'true';
            } else {
              my = 'false';
            }
            $this.ajax({
              async: false,
                  timeout: 30000,
                  url: $this.url + '?action=state&type=lobby&modified=0&player_id=' + player_id + '&in_progress=' + query_in_progress + '&my=' + my,
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
            this.set_active(root, element);
            this.notify_active(root, 'in_progress');
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
            this.set_active(root, element);
            this.notify_active(root, 'finished');
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
                if(game.invited.length === 0 && game.players.length <= 1) {
                    deferred = this.advertise(player_id, game.id, root);
                } else {
                    deferred = this.invitation_owner(player_id, game, root);
                }
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

        invitation_owner: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_owner', root);
            this.set_active(root, element);
            this.notify_active(root, 'invitation_owner');
            $('.cardstories_sentence', element).text(game.sentence);
            //
            // Proceed to vote, if possible
            //
            var voting = $('.cardstories_voting', element);
            voting.toggleClass('cardstories_ready', game.ready);
            if(game.ready) {
                voting.unbind('click').click(function() {
                    $this.send_game(player_id, game.id, element, 'action=voting&owner_id=' + player_id + '&game_id=' + game.id);
                });
            }
            //
            // Navigate to invite more friends, if desired
            //
            var invite_friends = $('.cardstories_invite_friends', element);
            invite_friends.unbind('click').click(function() {
                $.cookie('CARDSTORIES_INVITATIONS', null);
                $this.advertise(player_id, game.id, root);
            });
            //
            // display the cards picked by the current players
            //
            var players = game.players;
            var waiting = element.metadata({type: "attr", name: "data"}).waiting;
            var count = $('.cardstories_card', element).length;
            var cards = [];
            for(var i = 0; i < count; i++) {
                var card;
                if(i < players.length) {
                    card = { 'value': players[i][3],
                             'label': players[i][0] };
                } else {
                    card = { 'value': null,
                             'label': waiting };
                }
                cards.push(card);
            }
            var hand = $('.cardstories_cards_hand', element);
            return this.display_or_select_cards('invitation_owner', cards, undefined, hand);
        },

        invitation_pick: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick', root);
            this.set_active(root, element);
            this.notify_active(root, 'invitation_pick');
            this.invitation_board(player_id, game, root, element);
            var ok = function(card) {
                $this.send_game(player_id, game.id, element, 'action=pick&player_id=' + player_id + '&game_id=' + game.id + '&card=' + card);
            };
            var cards = $.map(game.self[2], function(card,index) { return {'value':card}; });
            return $this.select_cards('invitation_pick', cards, ok, element);
        },

        invitation_pick_wait: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick_wait', root);
            this.set_active(root, element);
            this.notify_active(root, 'invitation_pick_wait');
            $('.cardstories_sentence', element).text(game.sentence);
            var card = game.self[0];
            $('.cardstories_card', element).attr('class', 'cardstories_card cardstories_wait_card' + card + ' {card:' + card + '}');
            $('.cardstories_card_change', element).unbind('click').click(function() {
                $this.invitation_pick(player_id, game, root);
            });
        },

        select_cards: function(id, cards, ok, element) {
            var confirm = $('.cardstories_card_confirm', element);
            var middle = confirm.metadata({type: "attr", name: "data"}).middle;
            var confirm_callback = function(card, index, nudge, cards_element) {
                confirm.show();
                var wrapper = confirm.closest('.cardstories_active');
                wrapper.toggleClass('cardstories_card_confirm_right', index >= middle);
                $('.cardstories_card_confirm_ok', confirm).unbind('click').click(function() {
                    confirm.hide();
                    ok(card);
                    wrapper.removeClass('cardstories_card_confirm_right');
                    nudge();
                });
                $('.cardstories_card_confirm_cancel', confirm).unbind('click').click(function() {
                    confirm.hide();
                    wrapper.removeClass('cardstories_card_confirm_right');
                    nudge();
                });
            };
            var hand = $('.cardstories_cards_hand', element);
            return this.display_or_select_cards(id, cards, confirm_callback, hand);
        },

        display_or_select_cards: function(id, cards, select_callback, element) {
            // In create_pick_card, jqDock needs to start collapsed, to better
            // integrate with the animation.
            var start_collapsed = id === 'create_pick_card';
            id += '_saved_element';
            if(this[id] === undefined) {
                this[id] = element.html();
            } else {
                element.html(this[id]);
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
              this.set_active(root, element);
              this.notify_active(root, 'invitation_participate');
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
            this.set_active(root, element);
            this.notify_active(root, 'invitation_anonymous');
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
            this.set_active(root, element);
            this.notify_active(root, 'vote_viewer');
            $('.cardstories_sentence', element).text(game.sentence);
            var cards = game.board;
            $('.cardstories_card', element).each(function(index) {
                var c = 'cardstories_card cardstories_card' + cards[index] + ' {card:' + cards[index] + '}';
                $(this).attr('class', c);
            });
        },

        vote_voter: function(player_id, game, root) {
            var element = $('.cardstories_vote .cardstories_voter', root);
            this.set_active(root, element);
            this.notify_active(root, 'vote_voter');
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
            return $this.select_cards('vote_voter', cards, ok, element);
        },

        vote_voter_wait: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_voter_wait', root);
            this.set_active(root, element);
            this.notify_active(root, 'vote_voter_wait');
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
            this.set_active(root, element);
            this.notify_active(root, 'vote_anonymous');
            $('.cardstories_sentence', element).text(game.sentence);
        },

        vote_owner: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_owner', root);
            this.set_active(root, element);
            this.notify_active(root, 'vote_owner');
            $('.cardstories_sentence', element).text(game.sentence);
            // Activate the button to publish the results if the game is ready
            var finish = $('.cardstories_finish', element);
            finish.toggleClass('cardstories_ready', game.ready);
            if(game.ready) {
                finish.click(function() {
                    $this.confirm_results_publication(player_id, game, root);
                });
            }
            
            // Display the current board state
            this.results_board(player_id, game, element);
        },

        confirm_results_publication: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_confirm_results_publication', root);
            var vote_element = $('.cardstories_vote .cardstories_owner', root);
            this.set_active(root, element);
            this.notify_active(root, 'confirm_results_publication');
            $('.cardstories_notyet_announce_results').click(function () {
                $this.vote_owner(player_id, game, root);
            });
            $('.cardstories_announce_results').click(function () {
                $this.send_game(player_id, game.id, vote_element, 'action=complete&owner_id=' + player_id + '&game_id=' + game.id);
            });
        },

        complete: function(player_id, game, root) {
            var $this = this;
            if (game.owner) {
                $('.play_again', root).show();
                $('.play_again', root).unbind('click').click(function () {
                    // "Play again" in this case is just to create a new game and
                    // the players of this game will be kept as well because
                    // the CARDSTORIES_INVITATIONS cookie stores those playes emails.
                    $this.create(player_id, root);
                });
            } else {
                $('.play_again').hide();
            }
            var element = $('.cardstories_complete', root);
            this.set_active(root, element);
            this.notify_active(root, 'complete');
            element.toggleClass('cardstories_owner', game.owner);
            element.toggleClass('cardstories_player', !game.owner);
            $('.cardstories_set_why', element).unbind('click').click(function() {
                element.toggleClass('cardstories_why', true);
            });
            $('.cardstories_unset_why', element).unbind('click').click(function() {
                element.toggleClass('cardstories_why', false);
            });
            // Display the current board state
            this.results_board(player_id, game, element);
        },

        results_board: function(player_id, game, element) {
            $('.cardstories_sentence', element).text(game.sentence);

            var i;
            var board2voters = {};
            for(i = 0; i < game.board.length; i++) {
              board2voters[game.board[i]] = [];
            }
            var board2player = {};
            var winners = [];
            for(i = 0; i < game.players.length; i++) {
              var vote = game.players[i][1];
              var picked = game.players[i][3];
              var voters = board2voters[vote];
              if(voters !== undefined) {
                voters.push(game.players[i][0]);
              }
              if(game.players[i][2] == 'y') {
                winners.push(game.players[i][0]);
              }
              board2player[picked] = game.players[i];
            }
            
            $('.cardstories_winners', element).text(winners.join(', '));

            var cards = game.board;
            $('.cardstories_column', element).each(function(index) {
                if(index < cards.length) {
                  var card = cards[index];
                  $(this).toggleClass('cardstories_winner_card', game.winner_card == card);
                  var c = 'cardstories_card cardstories_complete_card' + card + ' {card:' + card + '}';
                  $('.cardstories_card', this).attr('class', c);
                  var player = board2player[card];
                  if(player !== undefined) {
                    $('.cardstories_player_name', this).toggleClass('cardstories_win', player[2] == 'y');
                    $('.cardstories_player_name', this).text(player[0]);
                  }
                  var voters = board2voters[card];
                  if(voters !== undefined) {
                    $('.cardstories_voter_name', this).each(function(voter_index) {
                        if(voters.length > voter_index) {
                          $(this).text(voters[voter_index]);
                          $(this).show();
                        } else {
                          $(this).hide();
                        }
                      });
                  }
                  $(this).show();
                } else {
                  $(this).hide();
                }
            });
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
            $this.ajax({
                async: false,
                timeout: 30000,
                url: $this.url + '?action=state&type=game&modified=0&game_id=' + game_id + '&player_id=' + player_id,
                type: 'GET',
                dataType: 'json',
                global: false,
                success: success,
                error: $this.xhr_error
            });
        },

        unset_active: function(root) {
            $('.cardstories_active', root).removeClass('cardstories_active');
        },

        set_active: function(root, element) { 
            this.unset_active(root);
            $(element).addClass('cardstories_active');
            $(element).parents('.cardstories_root div').addClass('cardstories_active');
        },

        notify_active: function(root, skin) {
            $(root).trigger('active.cardstories', [skin]);
        },

        email: function(game_id, root) {
            var $this = this;
            var element = $('.cardstories_subscribe', root);
            this.set_active(root, element);
            this.notify_active(root, 'email');
            validator = $(".cardstories_emailform", element).validate({
                submitHandler: function(form) {
                    var player_id = encodeURIComponent($('.cardstories_email', element).val());
                    $.cookie('CARDSTORIES_ID', player_id);
                    $this.game_or_lobby(player_id, game_id, root);        
                }
            });

            $('.cardstories_email', element).focus();
        },

        login: function(welcome_url, game_id, root) {
            if(welcome_url !== undefined && welcome_url !== null && welcome_url !== '') {
                $.cardstories.location.href = welcome_url;
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
             if(game_id === undefined || game_id === '') {
               this.refresh_lobby(player_id, true, true, root);
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
