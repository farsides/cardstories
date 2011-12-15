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
from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic.simple import direct_to_template

admin.autodiscover()

# Django contrib urls.
urlpatterns = patterns('',
    url(r'^password/reset/$', auth_views.password_reset, name='auth_password_reset'),
    url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', auth_views.password_reset_confirm, name='auth_password_reset_confirm'),
    url(r'^password/reset/complete/$', auth_views.password_reset_complete, name='auth_password_reset_complete'),
    url(r'^password/reset/done/$', auth_views.password_reset_done, name='auth_password_reset_done'),
    (r'^admin/', include(admin.site.urls)),
)

# Application urls.
urlpatterns += patterns('website.cardstories.views',
    (r'^$', 'welcome'),
    (r'^register/', 'register'),
    (r'^login/', 'login'),
    (r'^logout/', 'logout'),
    (r'^facebook/', 'facebook'),
    (r'^get_player_id/(.+)/', 'get_player_id'),
    (r'^get_player_name/(\d+)/', 'get_player_name'),
    (r'^get_player_email/(\d+)/', 'get_player_email'),
    (r'^get_loggedin_player_id/(.+)/', 'get_loggedin_player_id'),
)

# Development urls
if settings.DEBUG:
    # Serve media statically
    media_url = settings.MEDIA_URL
    if media_url.startswith('/'):
        media_url = media_url[1:]
        urlpatterns += patterns('',
            (r'^%s(?P<path>.*)$' % media_url, 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
        )

    # Proxy requests to the cardstories service.
    urlpatterns += patterns('',
        (r'^resource', 'website.util.views.proxy', {'cardstories_host': settings.CARDSTORIES_HOST}),
    )
