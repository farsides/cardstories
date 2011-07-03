#!/usr/bin/env python
#
# Copyright (C) 2011 Farsides <contact@farsides.com>
#
# Author: Adolfo R. Brandes <arbrandes@gmail.com>
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
import coverage

from django.test.simple import run_tests
from django.conf import settings
 
def run_tests_with_coverage(test_labels, verbosity=1, interactive=True,
                            extra_tests=[]):
    """
    Test runner which displays a code coverage report at the end of the
    run.  It will not display coverage if:

    a) The COVERAGE_MODULES setting is not set.
    b) A specific app is being tested.
    """
    if hasattr(settings, 'COVERAGE_MODULES') and not test_labels:
        enable_coverage = True
    else:
        enable_coverage = False

    if enable_coverage:
        coverage.use_cache(0)
        coverage.start()
 
    results = run_tests(test_labels, verbosity, interactive, extra_tests)
 
    if enable_coverage:
        coverage.stop()
 
        print '-------------------------------------------------'
        print 'Coverage'
        print '-------------------------------------------------'
 
        # Report coverage
        coverage_modules = []
        for module in settings.COVERAGE_MODULES:
            coverage_modules.append(__import__(module, globals(), locals(), ['']))
 
        coverage.report(coverage_modules, show_missing=1)
 
        print '-------------------------------------------------'
 
    return results
