#
# This file is part of my.gpodder.org.
#
# my.gpodder.org is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# my.gpodder.org is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
# License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with my.gpodder.org. If not, see <http://www.gnu.org/licenses/>.
#

from django.contrib.auth.backends import ModelBackend
from django.core.validators import email_re
from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.core.urlresolvers import reverse

from mygpo.users.models import User


class EmailAuthenticationBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        if email_re.search(username):
            user = User.get_user_by_email(username)
            if not user:
                return None

            return user if user.check_password(password) else None
        return None

    def get_user(self, username):
        return User.get_user(username)


def get_google_oauth_flow(request):
    """ Prepare an OAuth 2.0 flow

    https://developers.google.com/api-client-library/python/guide/aaa_oauth """

    from oauth2client.client import OAuth2WebServerFlow

    site = RequestSite(request)

    callback = 'http{s}://{domain}{callback}'.format(
        s='s' if request.is_secure() else '',
        domain=site.domain,
        callback=reverse('login-google-callback'))

    flow = OAuth2WebServerFlow(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scope='https://www.googleapis.com/auth/userinfo.email',
        redirect_uri=callback)

    return flow
