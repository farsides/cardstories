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
import sys
import os
sys.path.insert(0, os.path.abspath("..")) # so that for M-x pdb works
from twisted.trial import unittest, runner, reporter
from twisted.web import client

from cardstories import tap

class CardstoriesServerTest(unittest.TestCase):
    def setUp(self):
        self.port = '14834'
        options = tap.Options()
        options.parseOptions(['--port', self.port, '--db', 'test.sqlite' ])
        self.service = tap.makeService(options)
        self.service.startService()

    def tearDown(self):
        return self.service.stopService()

    def test01_connect(self):
        d = client.getPage('http://127.0.0.1:%s/resource' % self.port)
        def check(result):
            self.assertEquals('{}', result)
        d.addCallback(check)
        return d

    def test02_parseOptions(self):
        settings = tap.Options()
        pem = 'cert.pem'
        db = 'base.sqlite'
        auth = 'basic'
        ssl_port = '8080'
        settings.parseOptions(['--port', self.port,
                               '--ssl-port', ssl_port,
                               '--ssl-pem', pem,
                               '--verbose',
                               '--db', db,
                               '--auth', auth,
                               '--auth-db', 'auth' + db,
                               ])
        self.assertEquals(pem, settings['ssl-pem'])
        self.assertEquals(1, settings['verbose'])
        self.assertEquals(db, settings['db'])
        self.assertEquals(auth, settings['auth'])
        self.assertEquals('auth' + db, settings['auth-db'])
        self.assertEquals(int(self.port), settings['port'])
        self.assertEquals(int(ssl_port), settings['ssl-port'])

        settings.parseOptions(['-p', self.port,
                               '-s', ssl_port,
                               '-P', pem,
                               '-v',
                               '-a', auth,
                               ])
        self.assertEquals(pem, settings['ssl-pem'])
        self.assertEquals(1, settings['verbose'])
        self.assertEquals(db, settings['db'])
        self.assertEquals(auth, settings['auth'])
        self.assertEquals(int(self.port), settings['port'])
        self.assertEquals(int(ssl_port), settings['ssl-port'])
        
# Dummy CERT borrowed from Debian's snake-oil certificate.  Including it
# here since I can't assume what distribution I am on.

snake_oil_cert = """-----BEGIN CERTIFICATE-----
MIIDKzCCApQCCQDEKuqSPjfcEDANBgkqhkiG9w0BAQUFADCB2TELMAkGA1UEBhMC
WFgxKjAoBgNVBAgTIVRoZXJlIGlzIG5vIHN1Y2ggdGhpbmcgb3V0c2lkZSBVUzET
MBEGA1UEBxMKRXZlcnl3aGVyZTEOMAwGA1UEChMFT0NPU0ExPDA6BgNVBAsTM09m
ZmljZSBmb3IgQ29tcGxpY2F0aW9uIG9mIE90aGVyd2lzZSBTaW1wbGUgQWZmYWly
czEXMBUGA1UEAxMObWFwbGUuc2ZsYy12cG4xIjAgBgkqhkiG9w0BCQEWE3Jvb3RA
bWFwbGUuc2ZsYy12cG4wHhcNMDkwMTAyMTg1NzA0WhcNMDkwMjAxMTg1NzA0WjCB
2TELMAkGA1UEBhMCWFgxKjAoBgNVBAgTIVRoZXJlIGlzIG5vIHN1Y2ggdGhpbmcg
b3V0c2lkZSBVUzETMBEGA1UEBxMKRXZlcnl3aGVyZTEOMAwGA1UEChMFT0NPU0Ex
PDA6BgNVBAsTM09mZmljZSBmb3IgQ29tcGxpY2F0aW9uIG9mIE90aGVyd2lzZSBT
aW1wbGUgQWZmYWlyczEXMBUGA1UEAxMObWFwbGUuc2ZsYy12cG4xIjAgBgkqhkiG
9w0BCQEWE3Jvb3RAbWFwbGUuc2ZsYy12cG4wgZ8wDQYJKoZIhvcNAQEBBQADgY0A
MIGJAoGBAO0t+HjxiiliSHO9kge943+cXHGCtJp4/RPpHDN7hbpblY+FYCjuCmW/
/m2G59aMMl2Uwj1BO8cDwdGDtkNV21vcIo0siSD9VREFiYcLthaOK98muqD+Tfqa
MuGzZyui1RKuirCZzqyJPS2SXOtWSXUW8YQa75y/o4vcQSWWZ3VDAgMBAAEwDQYJ
KoZIhvcNAQEFBQADgYEApx7Q+PzLgdJu7OQJ776Kr+EI+Ho03pM5Nb5e26P5ZL6h
hk+gRLfBt8q3bihx4qjBSOpx1Qxq+BAMg6SAkDzkz+tN2CSr/vv2uuc26cDaf1co
oKCay2gMThIoURl+FSPeWAraGWbrcVy9ctoCipxMza9fn42dbn9OHxP/M+0qgvY=
-----END CERTIFICATE-----
-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDtLfh48YopYkhzvZIHveN/nFxxgrSaeP0T6Rwze4W6W5WPhWAo
7gplv/5thufWjDJdlMI9QTvHA8HRg7ZDVdtb3CKNLIkg/VURBYmHC7YWjivfJrqg
/k36mjLhs2crotUSroqwmc6siT0tklzrVkl1FvGEGu+cv6OL3EEllmd1QwIDAQAB
AoGBAL4ws+QABIOE/YZaSKSOn8Rv1S1s23hXdtGlh2i9L5It6LOrB14q7AmFuPeJ
S5We3LBwHoZSLiY7nAtvLBO44GmwpSiJuLaI0z/7YIqkS6KjiDy1GFdQ5IEaRzxK
nyDcvES4h4QdOa/UeMEWg8TmasEoG3Wm3+aZt5KRz57HQQJRAkEA/uN0aw+1jqVP
YKbG89k7DEdNOdfgLjFofXruwXPfQmEFNg3Vp5ke1SeaR0tzYDXgZ5fDlwnR0EgA
HrR0om3PKwJBAO42vxdAVjrfMt0ws0wTmKS7mLlY8p7dKVKKIwP6F2b/61QyEX7z
czjyBaegw8qbX93OD0g2TETms73Py4WFJkkCQBV97FUSsAZlHfpSVbg9+uKgKHzW
HQsIE31xHiylro+USrIyHG/TU2w5uKKGVCYqpM9XVqCnrU9Yotnz8Vm41J0CQQCf
VccjikkjP8AJ61VCgakMJt7UuwYt9Mh7CSK6ukGFB5Ek1AiX3ccoQ9o8cXAEyUCq
X/Yg2xDQ1W9Mev0q5hDhAkBKSJF0V/24bz27z1yUSzHRHO3FAKXepkR81g6IRl41
r9nOQTOBo04TLBXtyP+o7GFNzBjEm6fVaqwk5SVsdQ+t
-----END RSA PRIVATE KEY-----
"""

class CardstoriesServerTestSSL(unittest.TestCase):
    def setUp(self):
        self.port = '14834'
        self.ssl_port = '14835'
        pem = "cardstories.pem"
        fd = open(pem, "w")
        fd.write(snake_oil_cert)
        fd.close()
        options = tap.Options()
        options.parseOptions(['--port', self.port, '--ssl-port', self.ssl_port, '--ssl-pem', pem, '--db', 'test.sqlite' ])
        self.service = tap.makeService(options)
        self.service.startService()

    def tearDown(self):
        return self.service.stopService()

    def test01(self):
        d = client.getPage('https://127.0.0.1:%s/resource' % self.ssl_port)
        def check(result):
            self.assertEquals('{}', result)
        d.addCallback(check)
        return d

def Run():
    loader = runner.TestLoader()
#    loader.methodPrefix = "test_trynow"
    suite = loader.suiteFactory()
    suite.addTest(loader.loadClass(CardstoriesServerTest))
    suite.addTest(loader.loadClass(CardstoriesServerTestSSL))

    return runner.TrialRunner(
        reporter.VerboseTextReporter,
        tracebackFormat='default',
        ).run(suite)

if __name__ == '__main__':
    if Run().wasSuccessful():
        sys.exit(0)
    else:
        sys.exit(1)

# Interpreted by emacs
# Local Variables:
# compile-command: "python-coverage -e ; python-coverage -x test_tap.py ; python-coverage -m -a -r ../cardstories/tap.py"
# End:
