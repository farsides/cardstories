#
# Copyright (C) 2011 Dachary <loic@dachary.org>
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation (FSF), either version 3 of the License, or (at your
# option) any later version of the AGPL published by the FSF.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program in a file in the toplevel directory called
# "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
#
all:

check:
	make -C tests check
	jscoverage --no-instrument=js/jquery.query-2.1.7.js static static-coverage

clean:
	make -C tests clean
	find . -name '*,cover' | xargs rm -f
	rm -fr static-coverage
	rm -f etc/cardstories/twisted/plugins/dropin.cache
	find . -name '*~' | xargs rm -f
	find . -name '*.pyc' | xargs rm -f
	rm -fr dist
	rm -fr static/cardstories.zip
	rm -f MANIFEST
	rm -fr build

