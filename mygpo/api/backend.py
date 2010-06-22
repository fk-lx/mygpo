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

from mygpo.api.models import ToplistEntry, Podcast, Subscription
from django.db.models import Max
from datetime import datetime, timedelta
import re

try:
    import json

    # Python 2.5 seems to have a different json module
    if not 'dumps' in dir(json):
        raise ImportError

except ImportError:
    import json


def get_podcasts_for_languages(languages=None, podcast_query=Podcast.objects.all()):
    if not languages:
        return Podcast.objects.all()

    regex = '^(' + '|'.join(languages) + ')'
    return podcast_query.filter(language__regex=regex)


def get_toplist(count, languages=None, types=None):
    """
    Returns count podcasts with the most subscribers (individual users)
    If languages is given as an array of 2-character languages codes, only
    podcasts with the given languages are considered

    For language-specific lists the entries' oldplace attribute is calculated
    based on the same language list
    """
    if not languages and not types:
        return ToplistEntry.objects.all()[:count]
    else:
        podcast_entries_base = ToplistEntry.objects.all()
        group_entries_base = ToplistEntry.objects.all()

        if languages:
            lang_regex = '^(' + '|'.join(languages) + ')'
            podcast_entries_base = podcast_entries_base.filter(podcast__language__regex=lang_regex)
            group_entries_base = group_entries_base.filter(podcast_group__podcast__language__regex=lang_regex).distinct()

        if types:
            type_regex = '.*(' + '|'.join(types) + ').*'
            print type_regex
            podcast_entries_base = podcast_entries_base.filter(podcast__content_types__regex=type_regex)
            group_entries_base = group_entries_base.filter(podcast_group__podcast__content_types__regex=type_regex).distinct()


        old_podcast_entries = list(podcast_entries_base.exclude(oldplace=0).order_by('oldplace')[:count])
        old_group_entries = list(group_entries_base.exclude(oldplace=0).order_by('oldplace')[:count])
        old_list = merge_toplists(old_podcast_entries, old_group_entries, lambda x: x.oldplace, reverse=False)
        old_items = [e.get_item() for e in old_list]

        podcast_entries = podcast_entries_base.order_by('-subscriptions')[:count]
        group_entries = group_entries_base.order_by('-subscriptions')[:count]
        cur_list = merge_toplists(podcast_entries, group_entries, lambda x: x.subscriptions, reverse=True, count=count)

        for x in cur_list:
            x.oldplace = old_items.index(x.get_item())+1 if x.get_item() in old_items else 0

        return cur_list


def merge_toplists(podcast_entries, group_entries, sortkey, reverse, count=None):
    """
    merges a podcast- and a group toplist based on the given sortkey
    """
    entries = list(podcast_entries)
    entries.extend(group_entries)
    entries.sort(key=sortkey, reverse=reverse)
    if count:
        entries = entries[:count]
    return entries


def get_random_picks(languages=None, recent_days=timedelta(days=7)):
#    threshold = datetime.today() - recent_days

    all_podcasts    = Podcast.objects.all().exclude(title='').order_by('?')
    lang_podcasts   = get_podcasts_for_languages(languages, all_podcasts)
#    recent_podcasts = lang_podcasts.annotate(latest_release=Max('episode__timestamp')).filter(latest_release__gt=threshold)

#    if recent_podcasts.count() > 0:
#        return recent_podcasts

    if lang_podcasts.count() > 0:
        return lang_podcasts

    else:
        return all_podcasts

def get_all_subscriptions(user):
    return set([s.podcast for s in Subscription.objects.filter(user=user)])

def get_public_subscriptions(user):
    subscriptions = [s for s in Subscription.objects.filter(user=user)]
    public_subscriptions = set([s.podcast for s in subscriptions if s.get_meta().public])
    return public_subscriptions

