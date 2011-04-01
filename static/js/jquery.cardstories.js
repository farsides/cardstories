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

        ajax: function(o) { return jQuery.ajax(o); },

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
            $('input[type=submit]', element).click(function() {
                var success = function(data, status) {
                    if('error' in data) {
                        $this.error(data.error);
                    } else {
                        var root = $(element).parents('.cardstories_root');
                        $this.setTimeout(function() { $this.game(player_id, data.game_id, root); }, 30);
                    }
                };
                var sentence = encodeURIComponent($('input[name="sentence"]', element).val());
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

        invitation: function(player_id, game, root) {
            if(game.owner) {
                this.invitation_owner(player_id, game, root);
            } else {
                if(game.self !== null && game.self !== undefined) {
                    this.invitation_pick(player_id, game, root);
                } else {
                    this.invitation_participate(player_id, game, root);
                }
            }
        },

        invitation_owner: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_owner', root);
            this.set_active(root, element);
            $('a.cardstories_invite').attr('href', '?game_id=' + game.id);
            $('a.cardstories_refresh').attr('href', '?player_id=' + player_id + '&game_id=' + game.id);
            var voting = $('.cardstories_voting', element);
            voting.toggleClass('cardstories_ready', game.ready);
            if(game.ready) {
                voting.click(function() {
                    $this.send(player_id, game.id, element, 'action=voting&owner_id=' + player_id + '&game_id=' + game.id);
                });
            }
        },

        invitation_pick: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_pick', root);
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(game.sentence);
            $('.cardstories_card', element).unbind('click').click(function() {
                var card = $(this).metadata().card;
                $this.send(player_id, game.id, element, 'action=pick&player_id=' + player_id + '&game_id=' + game.id + '&card=' + card);
            });
            var cards = game.self[2];
            $('.cardstories_card', element).each(function(index) {
                $(this).attr('class', 'cardstories_card cardstories_card' + cards[index] + ' {card:' + cards[index] + '}');
            });
        },

        invitation_participate: function(player_id, game, root) {
            var $this = this;
            var element = $('.cardstories_invitation .cardstories_participate', root);
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(game.sentence);
            $('input[type=submit]', element).click(function() {
                $this.send(player_id, game.id, element, 'action=participate&player_id=' + player_id + '&game_id=' + game.id);
            });
        },

        vote: function(player_id, game, root) {
            if(game.owner) {
                this.vote_owner(player_id, game, root);
            } else {
                if(game.self !== null && game.self !== undefined) {
                    this.vote_voter(player_id, game, root);
                } else {
                    this.vote_viewer(player_id, game, root);
                }
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
            var $this = this;
            var element = $('.cardstories_vote .cardstories_voter', root);
            this.set_active(root, element);
            $('.cardstories_sentence', element).text(game.sentence);
            var cards = game.board;
            var picked = game.self[0];
            var voted = game.self[1];
            $('.cardstories_card', element).each(function(index) {
                var c = 'cardstories_card cardstories_card' + cards[index] + ' {card:' + cards[index] + '}';
                if(picked == cards[index]) {
                    c += ' cardstories_picked';
                }
                if(voted && voted == cards[index]) {
                    c += ' cardstories_voted';
                }
                $(this).attr('class', c);
            });
            $('.cardstories_card', element).not('.cardstories_picked').unbind('click').click(function() {
                var card = $(this).metadata().card;
                $this.send(player_id, game.id, element, 'action=vote&player_id=' + player_id + '&game_id=' + game.id + '&vote=' + card);
            });
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
                    $this.send(player_id, game.id, element, 'action=complete&owner_id=' + player_id + '&game_id=' + game.id);
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
            $('.cardstories_card', element).attr('class', 'cardstories_card cardstories_card' + game.winner_card + ' {card:' + game.winner_card + '}');
            $('.cardstories_player', element).each(function(index) {
                if(index < game.players.length) {
                  var player = game.players[index];
                  $(this).toggleClass('cardstories_win', player[2] == 'y');
                  $(this).text(player[0]);
                  $(this).show();
                } else {
                  $(this).hide();
                }
              });
        },

        send: function(player_id, game_id, element, query, data) {
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
                dataType: 'json',
                global: false,
                success: success,
                error: $this.xhr_error
            };
            if(data !== undefined) {
                request.type = 'POST';
                request.data = data;
            } else {
                request.type = 'GET';
            }
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
        },

        name: function(game_id, root) {
            var $this = this;
            var element = $('.cardstories_subscribe', root);
            $this.set_active(root, element);
            $('.cardstories_submit', element).click(function() {
                var player_id = encodeURIComponent($('.cardstories_name', element).val());
                $.cookie('CARDSTORIES_ID', player_id);
                $this.game_or_create(player_id, game_id, root);
              });
        },

        bootstrap: function(player_id, game_id, root) {
            if(player_id === undefined || player_id === null || player_id === '') {
              this.name(game_id, root);
            } else {
              this.game_or_create(player_id, game_id, root);
            }
        },

        game_or_create: function(player_id, game_id, root) {
             if(game_id === undefined || game_id === '') {
               this.create(player_id, root);
             } else {
               this.game(player_id, game_id, $(root));
             }
        }

    };

    $.fn.cardstories = function(player_id, game_id) {
        if(player_id === undefined || player_id === '') {
          player_id = $.cookie('CARDSTORIES_ID');
        }
        return this.each(function() {
            $(this).toggleClass('cardstories_root', true);
            $.cardstories.bootstrap(player_id, game_id, this);
            return this;
        });
    };

})(jQuery);
