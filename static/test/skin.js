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

    $.cardstories.skin = function(skin, root) {
        var stub_service = function(response, callback) {
            var original_ajax = $.cardstories.ajax;
            $.cardstories.ajax = function(opts) {
                $.cardstories.ajax = original_ajax;
                opts.success(response);
            };
        };

        // Stub out poll to not try to poll non-existing games.
        $.cardstories.poll = function() {};
        $.cardstories.poll_plugin = function() {};

        $(root).addClass('cardstories_root');
        var game;
        var old_game;

        // Init the audio plugin.
        $.cardstories_audio.init(undefined, undefined, root);

        // Don't try to resolve player info
        var rand_last_name = function() {
            if (Math.random() < 0.5) {
                return 'Name';
            } else {
                return 'Long Last Nameeeeeeeeee';
            }
        };
        $.cardstories.get_player_info_by_id = function(player_id) {
            return {
                name: 'Player ' + player_id + ' ' + rand_last_name(),
                avatar_url: '/static/css/images/avatars/default/' + player_id % 6 + '.jpg'
            };
        };

        // Stub the tabs interaction.
        $.cardstories_tabs.get_open_game_ids = function(root) { return []; };

        // Stub the table interactions.
        var table;
        var current_player_id;
        var owner_change_callback;
        $.cardstories_table.on_next_owner_change = function(player_id, game_id, root, callback) {
            owner_change_callback = callback;
            current_player_id = player_id;
        };
        var next_game_ready_callback;
        $.cardstories_table.on_next_game_ready = function(player_id, game_id, root, callback) {
            next_game_ready_callback = callback;
            current_player_id = player_id;
        };
        $.cardstories_table.get_next_owner_id = function(game_id, root) {
            return table.next_owner_id;
        };

        $('.cardstories_owner_change').unbind('click').click(function() {
            var next_owner_id;
            if (owner_change_callback) {
                if ($(this).hasClass('cardstories_owner_change_self')) {
                    next_owner_id = current_player_id;
                } else {
                    var player_ids = $.map(game.players, function(p) { return p.id; });
                    // Remove self and current next owner from potential candidates.
                    player_ids = $.grep(player_ids, function(id) {
                        return !(id === current_player_id || id === table.next_owner_id);
                    });
                    // Return a random candidate.
                    next_owner_id = player_ids[Math.floor(Math.random() * player_ids.length)];
                }
                table.next_owner_id = next_owner_id;
                owner_change_callback(next_owner_id);
            }
            return false;
        });
        $('.cardstories_next_game_ready').unbind('click').click(function() {
            if (next_game_ready_callback) {
                var opts;
                if ($(this).hasClass('cardstories_next_game_ready_self')) {
                    table.next_owner_id = current_player_id;
                    table.next_game_id = undefined;
                    opts = {force_create: true};
                } else {
                    table.next_owner_id = 42;
                    table.next_game_id = 4242;
                    opts = {};
                }
                next_game_ready_callback(table.next_game_id, opts);
            }
            return false;
        });

        if (skin === 'create_pick_card') {
            game = {
                id: 100,
                owner_id: 11,
                winner_card: null,
                sentence: null,
                self: [null, null, [1, 2, 3, 4, 5, 6]],
                players: [
                    {id: 1, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 2, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0}
                ]
            };
            table = {
                next_game_id: null,
                next_owner_id: null,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.create_pick_card(11, game, root);
        } else if (skin === 'create_wait_for_card') {
            game = {
                id: 101,
                owner_id: 1,
                winner_card: null,
                sentence: null,
                self: [null, null, []],
                players: [
                    {id: 1, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 2, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 3, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0}
                ]
            };
            table = {
                next_game_id: null,
                next_owner_id: null,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.create_wait_for_story(3, game, root);
        } else if (skin === 'create_wait_for_card_anonymous') {
            game = {
                id: 101,
                owner_id: 1,
                winner_card: null,
                sentence: null,
                self: [null, null, []],
                players: [
                    {id: 1, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 2, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 3, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 4, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 5, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0}
                ]
            };
            table = {
                next_game_id: null,
                next_owner_id: null,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.create_wait_for_story(42, game, root);
        } else if (skin === 'create_write_sentence') {
            game = {
                id: 100,
                owner_id: 11,
                winner_card: 25,
                sentence: null,
                players: [
                    {id: 1, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 2, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 3, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 4, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0}
                ]
            };
            table = {
                next_game_id: null,
                next_owner_id: null,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.create_write_sentence(11, game, root);
        } else if (skin === 'create_wait_for_sentence') {
            game = {
                id: 101,
                owner_id: 1,
                winner_card: '',
                sentence: null,
                self: [null, null, []],
                players: [
                    {id: 1, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 2, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 3, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 4, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 5, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0}
                ]
            };
            table = {
                next_game_id: null,
                next_owner_id: null,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.create_wait_for_story(2, game, root);
        } else if (skin === 'create_wait_for_sentence_anonymous') {
            game = {
                id: 101,
                owner_id: 1,
                winner_card: '',
                sentence: null,
                self: [null, null, []],
                players: [
                    {id: 1, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 2, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 3, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 4, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0},
                    {id: 5, vote: null, win: 'n', picked: null, cards: [], score: 0, levelups: 0}
                ]
            };
            table = {
                next_game_id: null,
                next_owner_id: null,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.create_wait_for_story(42, game, root);
        } else if (skin === 'invitation_owner') {
            game = {
                id: 100,
                owner: true,
                owner_id: 10,
                ready: false,
                sentence: 'long sentence is in the flux',
                winner_card: 7,
                players: [
                    {id: 10, vote: null, win: 'n', picked: null, cards: []},
                    {id: 1, vote: null, win: 'n', picked: null, cards: []},
                    {id: 2, vote: null, win: 'n', picked: 2, cards: []}
                ]
            };

            $.cardstories.invitation_owner(0, game, root);
        } else if (skin === 'invitation_owner_ready') {
            game = {
                id: 100,
                owner: true,
                owner_id: 10,
                ready: true,
                sentence: 'long sentence is in the flux',
                winner_card: 7,
                countdown_finish: $.now() + 60000,
                players: [
                    {id: 10, vote: null, win: 'n', picked: null, cards: []},
                    {id: 1, vote: null, win: 'n', picked: 1, cards: []},
                    {id: 2, vote: null, win: 'n', picked: 2, cards: []},
                    {id: 3, vote: null, win: 'n', picked: 3, cards: []},
                    {id: 4, vote: null, win: 'n', picked: 4, cards: []},
                    {id: 5, vote: null, win: 'n', picked: 5, cards: []}
                ]
            };

            $.cardstories.invitation_owner(0, game, root);
        } else if (skin === 'invitation_pick') {
            game = {
                id: 100,
                owner: false,
                owner_id: 10,
                player_id: 5,
                sentence: 'long sentence is in the flux',
                self: [35, null, [11,12,13,14,15,16,17]],
                players: [
                    {id: 10, vote: null, win: 'n', picked: 30, cards: []},
                    {id: 1, vote: null, win: 'n', picked: 31, cards: []},
                    {id: 2, vote: null, win: 'n', picked: 32, cards: []},
                    {id: 3, vote: null, win: 'n', picked: 33, cards: []},
                    {id: 4, vote: null, win: 'n', picked: 34, cards: []},
                    {id: 5, vote: null, win: 'n', picked: 35, cards: []}
                ]
            };
            $.cardstories.invitation_pick(5, game, root);
        } else if (skin === 'invitation_anonymous') {
            game = {
                id: 100,
                owner_id: 10,
                sentence: 'long sentence is in the flux',
                players: [
                    {id: 10, vote: null, win: 'n', picked: 30, cards: []},
                    {id: 1, vote: null, win: 'n', picked: 31, cards: []},
                    {id: 2, vote: null, win: 'n', picked: 32, cards: []},
                    {id: 3, vote: null, win: 'n', picked: null, cards: []},
                    {id: 4, vote: null, win: 'n', picked: 34, cards: []},
                    {id: 5, vote: null, win: 'n', picked: null, cards: []}
                ]
            };
            $.cardstories.invitation_anonymous(42, game, root);
        } else if (skin === 'invitation_pick_wait') {
            game = {
                id: 100,
                owner_id: 10,
                player_id: 3,
                self: [33, null, [11,12,13,14,15,16,17]],
                sentence: 'long sentence is in the flux',
                players: [
                    {id: 10, vote: null, win: 'n', picked: 30, cards: []},
                    {id: 1, vote: null, win: 'n', picked: '', cards: []},
                    {id: 2, vote: null, win: 'n', picked: null, cards: []},
                    {id: 3, vote: null, win: 'n', picked: 33, cards: []},
                    {id: 4, vote: null, win: 'n', picked: '', cards: []}
                ]
            };
            $.cardstories.invitation_pick_wait(3, game, root);
        } else if (skin === 'invitation_pick_wait_to_vote_voter') {
            old_game = {
                id: 100,
                board: [33,11,12,13,14,15],
                owner_id: 10,
                player_id: 3,
                self: [33, null, [11,12,13,14,15,33]],
                sentence: 'long sentence is in the flux',
                players: [
                    {id: 10, vote: null, win: 'n', picked: '', cards: null},
                    {id: 1, vote: null, win: 'n', picked: '', cards: null},
                    {id: 2, vote: null, win: 'n', picked: null, cards: null},
                    {id: 3, vote: null, win: 'n', picked: 33, cards: [11,12,13,14,15,33]},
                    {id: 4, vote: null, win: 'n', picked: '', cards: null}
                ]
            };
            game = $.extend(true, {}, old_game);
            game.players.splice(2,1);
            $.cardstories.invitation_pick_wait(3, old_game, root).done(function() {
                window.setTimeout(function() {
                    $.cardstories.invitation_pick_wait_to_vote_voter(3, old_game, game, root);
                }, 1000);
            });
        } else if (skin === 'vote_voter') {
            game = {
                id: 100,
                owner_id: 10,
                player_id: 2,
                ready: true,
                board: [32,31,30,33,35,34],
                self: [32, null, [32,31,30,33,35,34]],
                sentence: 'Fake sentence is fake',
                players: [
                    {id: 10, vote: null, win: 'n', picked: '', cards: null},
                    {id: 1, vote: null, win: 'n', picked: '', cards: null},
                    {id: 2, vote: null, win: 'n', picked: 32, cards: [32,31,30,33,35,34]},
                    {id: 3, vote: null, win: 'n', picked: '', cards: null},
                    {id: 4, vote: null, win: 'n', picked: '', cards: null},
                    {id: 5, vote: null, win: 'n', picked: '', cards: null}
                ]
            };
            $.cardstories.vote_voter(2, game, root);
        } else if (skin === 'vote_voter_wait') {
            game = {
                id: 100,
                owner_id: 10,
                player_id: 2,
                ready: true,
                board: [32,31,33,30,35,34],
                self: [32, 30, [32,31,30,33,35,34]],
                sentence: 'Fake sentence is fake',
                players: [
                    {id: 10, vote: null, win: 'n', picked: '', cards: null},
                    {id: 1, vote: null, win: 'n', picked: '', cards: null},
                    {id: 2, vote: 30, win: 'n', picked: 32, cards: [32,31,30,33,35,34]},
                    {id: 3, vote: '', win: 'n', picked: '', cards: null},
                    {id: 4, vote: null, win: 'n', picked: '', cards: null},
                    {id: 5, vote: '', win: 'n', picked: '', cards: null}
                ]
            };
            $.cardstories.vote_voter_wait(2, game, root);
        } else if (skin === 'vote_voter_wait_to_complete') {
            old_game = {
                id: 100,
                owner_id: 10,
                player_id: 2,
                ready: true,
                board: [32,31,33,30,35,34],
                self: [32, 30, [1,2,3,4,5,32]],
                winner_card: null,
                sentence: 'Fake sentence is fake',
                players: [
                    {id: 10, vote: null, win: 'n', picked: '', cards: null},
                    {id: 1, vote: '', win: 'n', picked: '', cards: null},
                    {id: 2, vote: '', win: 'n', picked: 32, cards: [1,2,3,4,5,32]},
                    {id: 3, vote: '', win: 'n', picked: '', cards: null},
                    {id: 4, vote: null, win: 'n', picked: '', cards: null},
                    {id: 5, vote: '', win: 'n', picked: '', cards: null}
                ]
            };
            game = $.extend(true, {}, old_game);
            game.winner_card = 30;
            game.players[0] = {id: 10, vote: null, win: 'y', picked: 30, cards: null};
            game.players[1] = {id: 1, vote: 35, win: 'n', picked: 31, cards: null};
            game.players[2] = {id: 2, vote: 30, win: 'y', picked: 32, cards: [1,2,3,4,5,32]};
            game.players[3] = {id: 3, vote: 35, win: 'n', picked: 33, cards: null};
            game.players[5] = {id: 4, vote: 30, win: 'y', picked: 35, cards: null};
            game.players.splice(4,1);
            $.cardstories.vote_voter_wait(2, old_game, root).done(function() {
                window.setTimeout(function() {
                    $.cardstories.vote_voter_wait_to_complete(2, old_game, game, root);
                }, 1000);
            });
        } else if (skin === 'vote_anonymous') {
            game = {
                id: 100,
                owner_id: 10,
                ready: true,
                board: [32,31,33,30,35,34],
                self: null,
                sentence: 'Fake sentence is fake',
                players: [
                    {id: 10, vote: null, win: 'n', picked: '', cards: null},
                    {id: 1, vote: null, win: 'n', picked: '', cards: null},
                    {id: 3, vote: '', win: 'n', picked: '', cards: null},
                    {id: 4, vote: null, win: 'n', picked: '', cards: null},
                    {id: 5, vote: '', win: 'n', picked: '', cards: null}
                ]
            };
            $.cardstories.vote_anonymous(null, game, root);
        } else if (skin === 'vote_owner') {
            game = {
                id: 100,
                owner_id: 10,
                ready: false,
                sentence: 'the game sentence',
                winner_card: 30,
                board: [32,31,30,33],
                players: [
                    {id: 10, vote: null, win: null, picked: 30, cards: []},
                    {id: 1, vote: null, win: null, picked: 31, cards: []},
                    {id: 2, vote: null, win: null, picked: 32, cards: []},
                    {id: 3, vote: 30, win: null, picked: 33, cards: []}
                ]
            };
            $.cardstories.vote_owner(0, game, root);
        } else if (skin === 'vote_owner_ready') {
            game = {
                id: 100,
                owner_id: 10,
                ready: true,
                sentence: 'the game sentence',
                board: [32,31,30,33,35,34],
                winner_card: 30,
                countdown_finish: $.now() + 15000,
                players: [
                    {id: 10, vote: null, win: null, picked: 30, cards: []},
                    {id: 1, vote: 32, win: null, picked: 31, cards: []},
                    {id: 2, vote: 30, win: null, picked: 32, cards: []},
                    {id: 3, vote: 30, win: null, picked: 33, cards: []},
                    {id: 4, vote: 31, win: null, picked: 34, cards: []},
                    {id: 5, vote: 31, win: null, picked: 35, cards: []}
                ]
            };
            $.cardstories.vote_owner(0, game, root);
        } else if (skin === 'complete') {
            game_id = 100;
            owner_id = 1;
            player_id = 2;
            game = {
                id: game_id,
                owner: false,
                owner_id: owner_id,
                player_id: player_id,
                ready: true,
                sentence: 'the game sentence',
                board: [30,31,32,33],
                self: [31, 30, [1,2,3,4,5,31]],
                winner_card: 30,
                players: [{id: owner_id,
                           vote: null,
                           win: 'n',
                           picked: 30,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: player_id,
                           vote: 32,
                           win: 'n',
                           picked: 31,
                           cards: [],
                           score: 12320,
                           level: 17,
                           score_next: 2950,
                           score_left: 1340,
                           score_prev: 12300,
                           level_prev: 17},
                          {id: 3,
                           vote: null,
                           win: 'n',
                           picked: 32,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 4,
                           vote: 30,
                           win: 'y',
                           picked: 34,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null}]
            };
            table = {
                next_game_id: null,
                next_owner_id: player_id,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.complete_complete(player_id, game, root);
        } else if (skin === 'complete_levelup') {
            game_id = 100;
            owner_id = 1;
            player_id = 12;
            game = {
                id: game_id,
                owner: false,
                owner_id: owner_id,
                player_id: player_id,
                ready: true,
                sentence: 'the game sentence',
                board: [30,31,32,33],
                self: [31, 30, [1,2,3,4,5,31]],
                winner_card: 30,
                players: [{id: owner_id,
                           vote: null,
                           win: 'y',
                           picked: 30,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 3,
                           vote: 30,
                           win: 'y',
                           picked: 34,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: player_id,
                           vote: 34,
                           win: 'n',
                           picked: 31,
                           cards: [],
                           score: 12320,
                           level: 7,
                           score_next: 2950,
                           score_left: 2340,
                           score_prev: 12300,
                           level_prev: 6,
                           earned_cards: [37,38,39,41,43],
                           earned_cards_cur: [43,41]}]
            };
            table = {
                next_game_id: null,
                next_owner_id: 2,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.complete_complete(player_id, game, root);
        } else if (skin === 'complete_owner') {
            game_id = 100;
            owner_id = 1;
            game = {
                id: game_id,
                owner: true,
                owner_id: owner_id,
                ready: true,
                sentence: 'the game sentence',
                board: [30,31,32,33,34,35],
                winner_card: 30,
                players: [{id: owner_id,
                           vote: null,
                           win: 'y',
                           picked: 30,
                           cards: [],
                           score: 12310,
                           level: 17,
                           score_next: 2950,
                           score_left: 1350,
                           score_prev: 12300,
                           level_prev: 17},
                          {id: 2,
                           vote: 32,
                           win: 'n',
                           picked: 31,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 3,
                           vote: 30,
                           win: 'y',
                           picked: 32,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 4,
                           vote: 35,
                           win: 'n',
                           picked: 33,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 5,
                           vote: 30,
                           win: 'y',
                           picked: 34,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 6,
                           vote: 30,
                           win: 'y',
                           picked: 35,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null}]
            };
            table = {
                next_game_id: null,
                next_owner_id: 2,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.complete_complete(owner_id, game, root);
        } else if (skin === 'complete_levelup_owner') {
            game_id = 100;
            owner_id = 1;
            game = {
                id: game_id,
                owner: true,
                owner_id: owner_id,
                ready: true,
                sentence: 'the game sentence',
                board: [30,31,32,33],
                self: [31, 30, [1,2,3,4,5,31]],
                winner_card: 30,
                players: [{id: owner_id,
                           vote: null,
                           win: 'y',
                           picked: 30,
                           cards: [],
                           score: 13,
                           level: 3,
                           score_next: 20,
                           score_left: 17,
                           score_prev: 11,
                           level_prev: 1},
                          {id: 2,
                           vote: 30,
                           win: 'y',
                           picked: 34,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 3,
                           vote: 34,
                           win: 'n',
                           picked: 31,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null}]
            };
            table = {
                next_game_id: null,
                next_owner_id: 2,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.complete_complete(owner_id, game, root);
        } else if (skin === 'complete_didnt_vote') {
            var owner_id = 10;
            var player3_id = 3;
            game = {
                id: 100,
                owner_id: owner_id,
                ready: true,
                sentence: 'the game sentence',
                board: [30,31,32,33,34,35],
                winner_card: 30,
                players: [{id: owner_id,
                           vote: null,
                           win: 'y',
                           picked: 30,
                           cards: [],
                           score: 12310,
                           level: 17,
                           score_next: 2950,
                           score_left: 1350,
                           score_prev: 12300,
                           level_prev: 17},
                          {id: 2,
                           vote: 32,
                           win: 'n',
                           picked: 31,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: player3_id,
                           vote: null,
                           win: 'y',
                           picked: 32,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 4,
                           vote: 32,
                           win: 'n',
                           picked: 33,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 5,
                           vote: 30,
                           win: 'y',
                           picked: 34,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null}]
            };
            table = {
                next_game_id: null,
                next_owner_id: 4,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.complete_complete(player3_id, game, root);
        } else if (skin === 'complete_anonymous') {
            var owner_id = 10;
            game = {
                id: 100,
                owner_id: owner_id,
                ready: true,
                sentence: 'the game sentence',
                board: [30,31,32,33,34,35],
                winner_card: 30,
                players: [{id: owner_id,
                           vote: null,
                           win: 'y',
                           picked: 30,
                           cards: [],
                           score: 12310,
                           level: 17,
                           score_next: 2950,
                           score_left: 1350,
                           score_prev: 12300,
                           level_prev: 17},
                          {id: 2,
                           vote: 32,
                           win: 'n',
                           picked: 31,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 3,
                           vote: null,
                           win: 'y',
                           picked: 32,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 4,
                           vote: 35,
                           win: 'n',
                           picked: 33,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 5,
                           vote: 30,
                           win: 'y',
                           picked: 34,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null},
                          {id: 6,
                           vote: 30,
                           win: 'y',
                           picked: 35,
                           cards: [],
                           score: null,
                           level: null,
                           score_next: null,
                           score_left: null,
                           score_prev: null,
                           level_prev: null}]
            };
            table = {
                next_game_id: null,
                next_owner_id: 4,
                on_next_owner_change_callback: null
            };
            $(root).data('cardstories_table', table);
            $.cardstories.complete_complete(42, game, root);
        } else if (skin === 'email') {
            $.cardstories.email(undefined, root);
        } else if (skin === 'credits') {
            $.cardstories.credits(root);
            $('.cardstories_credits_short', root).click();
        } else if (skin === 'panic') {
            $.cardstories.panic({code: 'PANIC', data: {game_id: 34, tb: 'Help!\nThe wheel fell off.'}});
        } else if (skin === 'game_does_not_exist') {
            stub_service({error: {code: 'GAME_DOES_NOT_EXIST', data: {game_id: 123}}});
            $.cardstories.game(12, 123, root);
        } else if (skin === 'game_full') {
            stub_service({error: {code: 'GAME_FULL', data: {game_id: 123, player_id: 12, max_players: 6}}});
            $.cardstories.player_participate(12, 123, root);
        } else if (skin === 'game_canceled') {
            $.cardstories.canceled(12, {}, root);
        } else if (skin === 'picked_too_late') {
            game = {
                id: 100,
                owner: false,
                owner_id: 10,
                sentence: 'long sentence is in the flux',
                self: [35, null, [11,12,13,14,15,16,17]],
                players: [
                    {id: 10, vote: null, win: 'n', picked: 30, cards: []},
                    {id: 1, vote: null, win: 'n', picked: 31, cards: []},
                    {id: 2, vote: null, win: 'n', picked: '', cards: []}
                ]
            };
            stub_service({error: {code: 'WRONG_STATE_FOR_PICKING', data: {game_id: 100, player_id: 2, state: 'vote'}}});
            $.cardstories.invitation_pick(2, game, root);
        } else if (skin === 'voted_too_late') {
            game = {
                id: 100,
                owner_id: 10,
                player_id: 2,
                ready: true,
                board: [32,31,30],
                self: [32, null, [32,31,30,33,35,34]],
                sentence: 'Fake sentence is fake',
                players: [
                    {id: 10, vote: null, win: 'n', picked: 30, cards: null},
                    {id: 1, vote: null, win: 'n', picked: 31, cards: null},
                    {id: 2, vote: null, win: 'n', picked: 32, cards: [32,31,30,33,35,34]}
                ]
            };
            stub_service({error: {code: 'GAME_NOT_LOADED', data: {game_id: 100}}});
            $.cardstories.vote_voter(2, game, root);
        }
    };

})(jQuery);
