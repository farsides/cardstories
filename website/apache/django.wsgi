import os
import sys

sitedir = 'website'
sitepath = os.path.join(os.path.dirname(
                        os.path.dirname(__file__)), sitedir)

if sitepath not in sys.path:
    sys.path.insert(0, sitepath)

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
