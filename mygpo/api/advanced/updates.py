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

from itertools import chain
from datetime import datetime

try:
    import gevent
except ImportError:
    gevent = None

from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.contrib.sites.models import RequestSite
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.views.generic.base import View

from mygpo.api.httpresponse import JsonResponse
from mygpo.api.advanced import clean_episode_action_data
from mygpo.api.advanced.directory import episode_data, podcast_data
from mygpo.utils import parse_bool, get_timestamp
from mygpo.users.models import DeviceDoesNotExist
from mygpo.users.subscriptions import subscription_changes, podcasts_for_states
from mygpo.api.basic_auth import require_valid_user, check_username
from mygpo.decorators import cors_origin
from mygpo.db.couchdb.episode import episodes_for_podcast
from mygpo.db.couchdb.episode_state import get_podcasts_episode_states
from mygpo.db.couchdb.podcast_state import podcast_states_for_device

from collections import namedtuple
EpisodeStatus = namedtuple('EpisodeStatus', 'episode status action')

import logging
logger = logging.getLogger(__name__)


class DeviceUpdates(View):
    """ returns various updates for a device

    http://wiki.gpodder.org/wiki/Web_Services/API_2/Devices#Get_Updates """

    @method_decorator(csrf_exempt)
    @method_decorator(require_valid_user)
    @method_decorator(check_username)
    @method_decorator(never_cache)
    @method_decorator(cors_origin())
    def get(self, request, username, device_uid):

        now = datetime.now()
        now_ = get_timestamp(now)

        user = request.user

        try:
            device = user.get_device_by_uid(device_uid)
        except DeviceDoesNotExist as e:
            return HttpResponseNotFound(str(e))

        try:
            since = self.get_since(request)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))

        include_actions = parse_bool(request.GET.get('include_actions', False))

        domain = RequestSite(request).domain

        add, rem, subscriptions = self.get_subscription_changes(device, since,
                                                                now, domain)
        updates = self.get_episode_changes(user, subscriptions, domain,
                                           include_actions, since)

        return JsonResponse({
            'add': add,
            'rem': rem,
            'updates': updates,
            'timestamp': get_timestamp(now),
        })


    def get_subscription_changes(self, device, since, now, domain):
        """ gets new, removed and current subscriptions """

        # DB: get all podcast states for the device
        podcast_states = podcast_states_for_device(device.id)

        add, rem = subscription_changes(device.id, podcast_states, since, now)

        subscriptions = filter(lambda s: s.is_subscribed_on(device), podcast_states)
        # DB get podcast objects for the subscribed podcasts
        subscriptions = podcasts_for_states(subscriptions)

        podcasts = dict( (p.url, p) for p in subscriptions )
        add = [podcast_data(podcasts.get(url), domain) for url in add ]

        return add, rem, subscriptions


    def get_episode_changes(self, user, subscriptions, domain, include_actions, since):
        devices = dict( (dev.id, dev.uid) for dev in user.devices )

        # index subscribed podcasts by their Id for fast access
        podcasts = dict( (p.get_id(), p) for p in subscriptions )

        episode_updates = self.get_episode_updates(user, subscriptions, since)

        return [self.get_episode_data(status, podcasts, domain,
                include_actions, user, devices) for status in episode_updates]


    def get_episode_updates(self, user, subscribed_podcasts, since,
            max_per_podcast=5):
        """ Returns the episode updates since the timestamp """

        if gevent:
            # DB: get max_per_podcast episodes for each subscribed podcast
            episode_jobs = [gevent.spawn(episodes_for_podcast, p, since,
                    limit=max_per_podcast) for p in subscribed_podcasts]
            gevent.joinall(episode_jobs)
            episodes = chain.from_iterable(job.get() for job in episode_jobs)

            # DB: get all episode states for all subscribed podcasts
            e_action_jobs = [gevent.spawn(get_podcasts_episode_states, p,
                    user._id) for p in subscribed_podcasts]
            gevent.joinall(e_action_jobs)
            e_actions = chain.from_iterable(job.get() for job in e_action_jobs)

        else:
            episodes = chain.from_iterable(episodes_for_podcast(p, since,
                    limit=max_per_podcast) for p in subscribed_podcasts)

            e_actions = chain.from_iterable(get_podcasts_episode_states(p,
                    user._id) for p in subscribed_podcasts)

        # TODO: get_podcasts_episode_states could be optimized by returning
        # only actions within some time frame

        e_status = { e._id: EpisodeStatus(e, 'new', None) for e in episodes}

        for action in e_actions:
            e_id = action['episode_id']

            if not e_id in e_status:
                continue

            episode = e_status[e_id].episode

            e_status[e_id] = EpisodeStatus(episode, action['action'], action)

        return e_status.itervalues()


    def get_episode_data(self, episode_status, podcasts, domain, include_actions, user, devices):
        """ Get episode data for an episode status object """

        # TODO: shouldn't the podcast_id be in the episode status?
        podcast_id = episode_status.episode.podcast
        podcast = podcasts.get(podcast_id, None)
        t = episode_data(episode_status.episode, domain, podcast)
        t['status'] = episode_status.status

        # include latest action (bug 1419)
        if include_actions and episode_status.action:
            t['action'] = clean_episode_action_data(episode_status.action, user, devices)

        return t

    def get_since(self, request):
        """ parses the "since" parameter """
        since_ = request.GET.get('since', None)
        if since_ is None:
            raise ValueError('parameter since missing')
        try:
            return datetime.fromtimestamp(float(since_))
        except ValueError as e:
            raise ValueError("'since' is not a valid timestamp: %s" % str(e))
