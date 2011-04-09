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

  $.cardstories.skin = function(what, root) {
    $(root).addClass('cardstories_root');
    var lobby = {'games': [[100, 'sentence100', 'invitation', 0],
                           [101, 'sentence101', 'vote', 1],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0],
                           [102, 'sentence102', 'invitation', 0]
                          ],
                 'wins': {100: 'n', 101: 'y' }
                };
    if(skin == 'advertise') {
      $.cardstories.advertise('PLAYER1', 100, root);
    } else if(skin == 'in_progress') {
      $.cardstories.lobbyInProgress('PLAYER1', lobby, root);
    } else if(skin == 'finished') {
      $.cardstories.lobbyFinished('PLAYER1', lobby, root);
    }
  }

})(jQuery);
