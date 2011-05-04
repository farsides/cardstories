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

        error: function(error) { alert(error); },

        xhr_error: function(xhr, status, error) {
            $.cardstories.error(error);
        },

        setTimeout: function(cb, delay) { return window.setTimeout(cb, delay); },

        ajax: function(o) {
            return jQuery.ajax(o);
        },

        reload: function(player_id, game_id, root) {
            var search = this.permalink(player_id, game_id, root);
            location.search = search;
        },

        permalink: function(player_id, game_id, root) {
            var search = '?player_id=' + player_id;
            if(game_id !== undefined && game_id !== '') {
              search += '&game_id=' + game_id;
            }
            return search;
        },

        create: function(player_id, root) {
            this.create_pick_card(player_id, root);
        },

        create_pick_card: function(player_id, root) {
            var $this = this;
            var element = $('.cardstories_create .cardstories_pick_card', root);
            this.set_active(root, element);
            $('.cardstories_card', element).click(function() {
                var card = $(this).metadata({type: "attr", name: "data"}).card;
                $this.create_write_sentence(player_id, card, root);
              });
            $('.cardstories_cards', element).jqDock({ active: 3 });
        },

        create_write_sentence: function(player_id, card, root) {
            var $this = this;
            var element = $('.cardstories_create .cardstories_write_sentence', root);
            this.set_active(root, element);
            $('.cardstories_card', element).attr('class', 'cardstories_card cardstories_card' + card + ' {card:' + card + '}');
            $('.cardstories_submit', element).unbind('click').click(function() {
                var success = function(data, status) {
                    if('error' in data) {
                        $this.error(data.error);
                    } else {
                        var root = $(element).parents('.cardstories_root');
                        $this.setTimeout(function() { $this.advertise(player_id, data.game_id, root); }, 30);
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
            });
        },

        advertise: function(owner_id, game_id, root) {
            var $this = this;
            var element = $('.cardstories_advertise', root);
            this.set_active(root, element);
            $('.cardstories_submit', element).unbind('click').click(function() {
                var text = $('.cardstories_text', element).val();
                var invites = text.split(/\s+/).
                              filter(function(s) { return s !== ''; }).
                              map(function(s) {
                                  return 'player_id=' + encodeURIComponent(s);
                                });
                
                $this.send_game(owner_id, game_id, element, 'action=invite&owner_id=' + owner_id + '&game_id=' + game_id + '&' + invites.join('&'));
              });
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
                    $this.reload(request.player_id, request.game_id, root);
                  }
                }
              }
            };
            var query = 'modified=' + request.modified;
            if('player_id' in request) {
              query += '&player_id=' + request.player_id;
            }
            if('game_id' in request) {
              query += '&game_id=' + request.game_id;
            }
            $this.ajax({
              async: true,
                  timeout: $this.poll_timeout * 2,
                  url: $this.url + '?action=poll&' + query,
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
                  $this.lobby_in_progress(player_id, data, root);
                } else {
                  $this.lobby_finished(player_id, data, root);
                }
                // FIXME not activated if the list of tables is empty ???
                $this.poll({ 'modified': data.modified, 'player_id': player_id }, root);
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
                  url: $this.url + '?action=lobby&player_id=' + player_id + '&in_progress=' + query_in_progress + '&my=' + my,
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
                                       'win': win,
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
            $('.cardstories_tab_in_progress', element).click(function() {
                $this.refresh_lobby(player_id, false, true, root);
              });
            $('.cardstories_start_story', element).click(function() {
                $this.start_story(player_id, root);
              });
            this.lobby_games(player_id, lobby, element, root);
        },

        lobby_finished: function(player_id, lobby, root) {
            var $this = this;
            var element = $('.cardstories_lobby .cardstories_finished', root);
            this.set_active(root, element);
            $('.cardstories_tab_finished', element).click(function() {
                $this.refresh_lobby(player_id, true, true, root);
              });
            $('.cardstories_start_story', element).click(function() {
                $this.start_story(player_id, root);
              });
            this.lobby_games(player_id, lobby, element, root);
        },

        invitation: function(player_id, game, root) {
            var poll = true;
            if(game.owner) {
                this.invitation_owner(player_id, game, root);
            } else {
                if(game.self !== null && game.self !== undefined) {
                    this.invitation_pick(player_id, game, root);
                    // do not disturb a player while (s)he is picking a card
                    poll = game.self[0] !== null;
                } else {
                    this.invitation_participate(player_id, game, root);
                }
            }
            if(poll) {
              this.poll({ 'modified': game.modified, 'game_id': game.id, 'player_id': player_id }, root);
            }
        },

        invitation_owner: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_owner', root);
            this.set_active(root, element);
            $('a.cardstories_invite').attr('href', '?game_id=' + game.id);
            $('a.cardstories_refresh').attr('href', '?player_id=' + player_id + '&game_id=' + game.id);
            var players = game.players;
            var meta = $('.cardstories_cards', element).metadata({type: "attr", name: "data"});
            $('.cardstories_card', element).each(function(index) {
                var card_file = meta.nocard;
                var title = meta.waiting;
                if(index < players.length) {
                  title = players[index][0];
                  var card = players[index][3];
                  if(card !== null) {
                    card_file = meta.card.supplant({'card': card});
                  }
                }
                $(this).attr('src', card_file);
                $(this).attr('title', title);
              });            
            $('.cardstories_cards', element).jqDock({ active: 3, labels: 'tc' });
            var voting = $('.cardstories_voting', element);
            voting.toggleClass('cardstories_ready', game.ready);
            if(game.ready) {
                voting.click(function() {
                    $this.send_game(player_id, game.id, element, 'action=voting&owner_id=' + player_id + '&game_id=' + game.id);
                });
            }
            var invite_friends = $('.cardstories_invite_friends', element);
            invite_friends.click(function() {
                var root = $(element).parents('.cardstories_root');
                $this.setTimeout(function() { $this.advertise(player_id, game.id, root); }, 30);
            });
        },

        invitation_pick: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick', root);
            this.set_active(root, element);
            this.player_select_card(player_id, game.id, game.sentence, game.self[2], 'pick', element, root);
            $('.cardstories_cards', element).jqDock({ active: game.self[2].length / 2});
        },

        player_select_card: function(player_id, game_id, sentence, cards, action, element, root) {
            var $this = this;
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(sentence);
            $('.cardstories_card', element).unbind('click').click(function() {
                var card = $(this).metadata({type: "attr", name: "data"}).card;
                $this.send_game(player_id, game_id, element, 'action=' + action + '&player_id=' + player_id + '&game_id=' + game_id + '&card=' + card);
            });
            var meta = $('.cardstories_cards', element).metadata({type: "attr", name: "data"});
            $('.cardstories_card', element).each(function(index) {
                var card = cards[index];
                var card_file = meta.nocard;
                if(index < cards.length) {
                  card_file = meta.card.supplant({'card': cards[index]});
                }
                $(this).attr('src', card_file);
                $(this).metadata({type: "attr", name: "data"}).card = card;
              });            
        },

        confirm_participate: false,

        invitation_participate: function(player_id, game, root) {
            var element = $('.cardstories_invitation .cardstories_participate', root);
            if(this.confirm_participate) {
              var $this = this;
              this.set_active(root, element);
              $('.cardstories_sentence', element).text(game.sentence);
              $('input[type=submit]', element).click(function() {
                  $this.send_game(player_id, game.id, element, 'action=participate&player_id=' + player_id + '&game_id=' + game.id);
                });
            } else {
              this.send_game(player_id, game.id, element, 'action=participate&player_id=' + player_id + '&game_id=' + game.id);
            }
        },

        vote: function(player_id, game, root) {
            var poll = true;
            if(game.owner) {
                this.vote_owner(player_id, game, root);
            } else {
                if(game.self !== null && game.self !== undefined) {
                    this.vote_voter(player_id, game, root);
                    // do not disturb a voting player while (s)he is voting
                    poll = game.self[1] !== null;
                } else {
                    this.vote_viewer(player_id, game, root);
                }
            }
            if(poll) {
                this.poll({ 'modified': game.modified, 'game_id': game.id, 'player_id': player_id }, root);
            }
        },

        vote_viewer: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_viewer', root);
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
            this.set_active(root, element);
            var cards = game.board;
            var $this = this;
            var picked = game.self[0];
            var voted = game.self[1];
            $('.cardstories_card', element).each(function(index) {
                var is_picked = picked == cards[index];
                if(is_picked) {
                  $(this).unbind('click');
                }
                if(is_picked) {
                  $(this).attr('title', 'My Card');
                } else {
                  $(this).removeAttr('title');
                }
            });
            this.player_select_card(player_id, game.id, game.sentence, cards, 'vote', element, root);
            $('.cardstories_cards', element).jqDock({ active: cards.length / 2, labels: 'tc'});
        },

        vote_owner: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_vote .cardstories_owner', root);
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(game.sentence);
            var finish = $('.cardstories_finish', element);
            finish.toggleClass('cardstories_ready', game.ready);
            if(game.ready) {
                finish.click(function() {
                    $this.send_game(player_id, game.id, element, 'action=complete&owner_id=' + player_id + '&game_id=' + game.id);
                });
            }

            var i;
            var board2voters = {};
            for(i = 0; i < game.board.length; i++) {
              board2voters[game.board[i]] = [];
            }
            for(i = 0; i < game.players.length; i++) {
              var vote = game.players[i][1];
              var voters = board2voters[vote];
              if(voters !== undefined) {
                voters.push(game.players[i][0]);
              }
            }
            var cards = game.board;
            $('.cardstories_card', element).each(function(index) {
                var card = cards[index];
                var c = 'cardstories_card cardstories_card' + card + ' {card:' + card + '}';
                $(this).attr('class', c);
                
                var voters = board2voters[card];
                if(voters !== undefined) {
                  var siblings = $(this).siblings('.cardstories_results');
                  $('.cardstories_result', siblings).each(function(voter_index) {
                      if(voters.length > voter_index) {
                        $(this).text(voters[voter_index]);
                        $(this).show();
                      } else {
                        $(this).hide();
                      }
                    });
                }
            });
        },

        complete: function(player_id, game, root) {
            var element = $('.cardstories_complete', root);
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(game.sentence);
            var i;
            var board2voters = {};
            for(i = 0; i < game.board.length; i++) {
              board2voters[game.board[i]] = [];
            }
            var board2player = {};
            for(i = 0; i < game.players.length; i++) {
              var vote = game.players[i][1];
              var picked = game.players[i][3];
              var voters = board2voters[vote];
              if(voters !== undefined) {
                voters.push(game.players[i][0]);
              }
              board2player[picked] = game.players[i];
            }
            var cards = game.board;
            $('.cardstories_column', element).each(function(index) {
                if(index < cards.length) {
                  var card = cards[index];
                  var c = 'cardstories_card cardstories_complete_card' + card + ' {card:' + card + '}';
                  $('.cardstories_card', this).attr('class', c);
                  var player = board2player[card];
                  $('.cardstories_player', this).toggleClass('cardstories_win', player[2] == 'y');
                  $('.cardstories_player', this).text(player[0]);
                  var voters = board2voters[card];
                  if(voters !== undefined) {
                    $('.cardstories_voter', this).each(function(voter_index) {
                        if(voters.length > voter_index) {
                          $(this).text(voters[voter_index]);
                          $(this).show();
                        } else {
                          $(this).hide();
                        }
                      });
                  } else {
                    $('.cardstories_voter', this).hide();
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
            var success = function(data, status) {
                if('error' in data) {
                    $this.error(data.error);
                } else {
                    $this[data.state](player_id, data, root);
                }
            };
            $this.ajax({
                async: false,
                timeout: 30000,
                url: $this.url + '?action=game&game_id=' + game_id + '&player_id=' + player_id,
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

        name: function(game_id, root) {
            var $this = this;
            var element = $('.cardstories_subscribe', root);
            $this.set_active(root, element);
            $('.cardstories_submit', element).click(function() {
                var player_id = encodeURIComponent($('.cardstories_name', element).val());
                $.cookie('CARDSTORIES_ID', player_id);
                $this.game_or_lobby(player_id, game_id, root);
              });
        },

        bootstrap: function(player_id, game_id, root) {
            if(player_id === undefined || player_id === null || player_id === '') {
              this.name(game_id, root);
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

    $(window).bind("beforeunload", function() {
        $.cardstories.error = function(error) { };
      });

})(jQuery);
