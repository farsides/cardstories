import os
import sys

projectpath = os.path.dirname(
	      os.path.dirname(
	      os.path.dirname(__file__)))
if projectpath not in sys.path:
    sys.path.insert(0, projectpath)

os.environ['DJANGO_SETTINGS_MODULE'] = 'website.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
