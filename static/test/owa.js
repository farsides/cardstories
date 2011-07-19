//
//     Copyright (C) 2011 Farsides <contact@farsides.com>
//
//     Author: Adolfo R. Brandes <arbrandes@gmail.com>
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
module('owa');

test('owa', function() {
    expect(9);

    var siteid = '1234567890';
    var url = 'http://bogus.url/';

    $('#owa').owa(url, siteid, false);
    equal($('script').first().attr('src'), url + 'modules/base/js/owa.tracker-combined-min.js');
    ok($.isArray(owa_cmds), 'owa_cmds should be an array');
    ok(owa_cmds.length > 0, 'owa_cmds should not be empty');
    var found_siteid = false;
    var found_trackpageview = false;
    for (var i = 0; i < owa_cmds.length; i++) {
        if (owa_cmds[i][0] == 'setSiteId') {
            found_siteid = i;
        } else if (owa_cmds[i][0] == 'trackPageView') {
            found_trackpageview = i;
        }
    }
    strictEqual(found_trackpageview, false, 'trackPageView should not be set');
    notStrictEqual(found_siteid, false, 'setSideId should be set');
    deepEqual(owa_cmds[found_siteid], ['setSiteId', siteid]);

    delete owa_cmds;
    $('#owa').owa(url, siteid, true);
    ok($.isArray(owa_cmds), 'owa_cmds should be an array');
    ok(owa_cmds.length > 0, 'owa_cmds should not be empty');
    found_trackpageview = false;
    for (var i = 0; i < owa_cmds.length; i++) {
        if (owa_cmds[i][0] == 'trackPageView') {
            found_trackpageview = i;
            break;
        }
    }
    notStrictEqual(found_trackpageview, false, 'trackPageView should be set');
});

test('owa_subscribe', function() {
    expect(2);

    var stream = 'bogus.stream';
    var host = 'www.bogus.com';
    var path = 'bogus/path/?coconut=';
    var state = 'kewlstate';
    var location = $.owa.location;
    $.owa.location = {protocol: 'http:', host: host};
    window['owa_cmds'] = [];
    $('#owa').owa_subscribe(stream, path);
    $('#owa').trigger(stream, [state]);
    stop();
    var interval = setInterval(function() {
        if (owa_cmds.length > 0) {
            var found = false;
            for (var i = 0; i < owa_cmds.length; i++) {
                if (owa_cmds[i][0] == 'trackPageView') {
                    found = i;
                    break;
                }
            }
            notStrictEqual(found, false, 'trackPageView should be set');
            deepEqual(owa_cmds[found], ['trackPageView', 'http://' + host + '/' + path + state]);
            clearInterval(interval);
            start();
        }
    }, 750);

    $.owa.location = location;
});
