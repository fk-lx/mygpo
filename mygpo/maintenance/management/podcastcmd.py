from itertools import islice, chain, imap as map
from optparse import make_option
import random

from django.core.management.base import BaseCommand

from mygpo.core.podcasts import individual_podcasts
from mygpo.directory.toplist import PodcastToplist
from mygpo.db.couchdb.podcast import podcast_by_id, podcast_for_url, \
         random_podcasts, podcasts_by_last_update, podcasts_need_update, \
         podcasts_by_next_update


class PodcastCommand(BaseCommand):
    """ command that operates on a list of podcasts specified by parameters """

    option_list = BaseCommand.option_list + (
        make_option('--toplist', action='store_true', dest='toplist',
            default=False, help="Update all entries from the Toplist."),

        make_option('--update-new', action='store_true', dest='new',
            default=False, help="Update all podcasts with new Episodes"),

        make_option('--max', action='store', dest='max', type='int',
            default=0, help="Set how many feeds should be updated at maximum"),

        make_option('--random', action='store_true', dest='random',
            default=False, help="Update random podcasts, best used with --max"),

        make_option('--next', action='store_true', dest='next',
            default=False, help="Podcasts that are due to be updated next"),
        )



    def get_podcasts(self, *args, **options):
        return chain.from_iterable(self._get_podcasts(*args, **options))


    def _get_podcasts(self, *args, **options):

        max_podcasts = options.get('max')

        if options.get('toplist'):
            yield (p.url for p in self.get_toplist(max_podcasts))

        if options.get('new'):
            podcasts = list(podcasts_need_update(limit=max_podcasts))
            random.shuffle(podcasts)
            yield (p.url for p in podcasts)

        if options.get('random'):
            # no need to pass "max" to random_podcasts, it uses chunked queries
            podcasts = random_podcasts()
            yield (p.url for p in individual_podcasts(podcasts))

        if options.get('next'):
            podcasts = podcasts_by_next_update(limit=max_podcasts)
            yield (p.url for p in individual_podcasts(podcasts))


        if args:
            yield args

        if not args and not options.get('toplist') and not options.get('new') \
                    and not options.get('random')  and not options.get('next'):
            podcasts = podcasts_by_last_update(limit=max_podcasts)
            yield (p.url for p in podcasts_by_last_update())


    def get_toplist(self, max_podcasts=100):
        toplist = PodcastToplist()
        return individual_podcasts(p for i, p in toplist[:max_podcasts])
