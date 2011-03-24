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
	    $this.error(error);
        },

        setTimeout: function(cb, delay) { return window.setTimeout(cb, delay); },

        ajax: function(o) { return jQuery.ajax(o); },

	create: function(player_id, element) {
	    var $this = this;
	    $('input[name="card"]:nth(0)', element).attr('checked','checked');
            $('input[type=submit]', element).click(function() {
                var success = function(data, status) {
                    if('error' in data) {
                        $this.error(data.error);
                    } else {
                        $this.setTimeout(function() { $this.game(player_id, data.game_id, element); }, 30);
		    }
                };
                var sentence = encodeURIComponent($('input[name="sentence"]', element).val());
		var card = $('input[name="card"]:checked', element).val();
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

	invitation: function(game, element) {
	},

	vote: function(game, element) {
	},

	complete: function(game, element) {
	},

	game: function(player_id, game_id, element) {
	    var $this = this;
            var success = function(data, status) {
		if('error' in data) {
                    $this.error(data.error);
		} else {
		    $this[$data.state](data, $('.cardstories_' + $data.state, element));
		}
            };
            $this.ajax({
		async: false,
		timeout: 30000,
		url: $this.url,
		type: 'GET',
		dataType: 'json',
		global: false,
		success: success,
		error: xhr_error
            });
	}
    };

    $.fn.cardstories = function(player_id, game_id) {
        return this.each(function() {
	    if(game_id === undefined) {
		$.cardstories.create(player_id, $('.cardstories_create', this));
	    } else {
		$.cardstories.game(player_id, game_id, $(this));
	    }
            return this;
        });
    };

})(jQuery);
