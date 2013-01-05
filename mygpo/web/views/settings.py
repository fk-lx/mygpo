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

from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth import logout
from django.contrib import messages
from django.forms import ValidationError
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import RequestSite
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import never_cache, cache_control
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from django.utils.html import strip_tags

from django_couchdb_utils.auth.models import UsernameException, \
         PasswordException

from mygpo.decorators import allowed_methods, repeat_on_conflict
from mygpo.web.forms import UserAccountForm, ProfileForm
from mygpo.web.utils import normalize_twitter
from mygpo.db.couchdb.podcast import podcast_by_id, podcasts_to_dict
from mygpo.db.couchdb.podcast_state import podcast_state_for_user_podcast, \
         subscriptions_by_user


@login_required
@vary_on_cookie
@cache_control(private=True)
@allowed_methods(['GET', 'POST'])
def account(request):

    if request.method == 'GET':

       userpage_token = request.user.get_token('userpage_token')

       profile_form = ProfileForm({
               'twitter': request.user.twitter,
               'about':   request.user.about,
            })

       form = UserAccountForm({
            'email': request.user.email,
            'public': request.user.settings.get('public_subscriptions', True)
            })

       return render(request, 'account.html', {
            'form': form,
            'profile_form': profile_form,
            'userpage_token': userpage_token,
            })

    try:
        form = UserAccountForm(request.POST)

        if not form.is_valid():
            raise ValueError(_('Oops! Something went wrong. Please double-check the data you entered.'))

        if form.cleaned_data['password_current']:
            if not request.user.check_password(form.cleaned_data['password_current']):
                raise ValueError('Current password is incorrect')

            request.user.set_password(form.cleaned_data['password1'])

        request.user.email = form.cleaned_data['email']

        try:
            request.user.save()
        except (UsernameException, PasswordException) as ex:
            messages.error(request, str(ex))

        messages.success(request, 'Account updated')

    except (ValueError, ValidationError) as e:
        messages.error(request, str(e))

    return render(request, 'account.html', {
        'form': form,
    })


class ProfileView(View):
    """ Updates the public profile and redirects back to the account view """

    def post(self, request):
        user = request.user

        form = ProfileForm(request.POST)

        if not form.is_valid():
            raise ValueError(_('Oops! Something went wrong. Please double-check the data you entered.'))

        request.user.twitter = normalize_twitter(form.cleaned_data['twitter'])
        request.user.about = strip_tags(form.cleaned_data['about'])

        request.user.save()
        messages.success(request, _('Data updated'))

        return HttpResponseRedirect(reverse('account'))



@login_required
@never_cache
@allowed_methods(['GET', 'POST'])
def delete_account(request):

    if request.method == 'GET':
        return render(request, 'delete_account.html')

    @repeat_on_conflict(['user'])
    def do_delete(user):
        user.is_active = False
        user.deleted = True
        user.save()

    do_delete(user=request.user)
    logout(request)

    return render(request, 'deleted_account.html')



class DefaultPrivacySettings(View):

    public = True

    @method_decorator(login_required)
    @method_decorator(never_cache)
    def post(self, request):
        self.set_privacy_settings(user=request.user)
        messages.success(request, 'Success')
        return HttpResponseRedirect(reverse('privacy'))

    @repeat_on_conflict(['user'])
    def set_privacy_settings(self, user):
        user.settings['public_subscriptions'] = self.public
        user.save()


class PodcastPrivacySettings(View):

    public = True

    @method_decorator(login_required)
    @method_decorator(never_cache)
    def post(self, request, podcast_id):
        podcast = podcast_by_id(podcast_id)
        state = podcast_state_for_user_podcast(request.user, podcast)
        self.set_privacy_settings(state=state)
        messages.success(request, 'Success')
        return HttpResponseRedirect(reverse('privacy'))

    @repeat_on_conflict(['state'])
    def set_privacy_settings(self, state):
        state.settings['public_subscription'] = self.public
        state.save()



@login_required
@never_cache
def privacy(request):
    site = RequestSite(request)

    subscriptions = subscriptions_by_user(request.user)
    podcasts = podcasts_to_dict([x[1] for x in subscriptions])

    included_subscriptions = set(filter(None, [podcasts.get(x[1], None) for x in subscriptions if x[0] == True]))
    excluded_subscriptions = set(filter(None, [podcasts.get(x[1], None) for x in subscriptions if x[0] == False]))

    return render(request, 'privacy.html', {
        'public_subscriptions': request.user.settings.get('public_subscriptions', True),
        'included_subscriptions': included_subscriptions,
        'excluded_subscriptions': excluded_subscriptions,
        'domain': site.domain,
        })


@vary_on_cookie
@cache_control(private=True)
@login_required
def share(request):
    site = RequestSite(request)

    if 'public_subscriptions' in request.GET:
        @repeat_on_conflict(['user'])
        def _update(user):
            user.subscriptions_token = ''
            user.save()

    elif 'private_subscriptions' in request.GET:
        @repeat_on_conflict(['user'])
        def _update(user):
            user.create_new_token('subscriptions_token')
            user.save()

    else:
        _update = None

    if _update:
        _update(user=request.user)

    token = request.user.get_token('subscriptions_token')

    return render(request, 'share.html', {
        'site': site,
        'token': token,
        })
