from django.core.management.base import BaseCommand
from mygpo.api import models
from mygpo.data import feeddownloader
from optparse import make_option
import datetime

UPDATE_LIMIT = datetime.datetime.now() - datetime.timedelta(days=15)

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--toplist', action='store_true', dest='toplist', default=False, help="Update all entries from the Toplist."),
        make_option('--update-new', action='store_true', dest='new', default=False, help="Update all podcasts with new Episodes"),
        make_option('--list-only', action='store_true', dest='list', default=False, help='Don\'t download/update anything, just list the podcasts to be updated'),
        )


    def handle(self, *args, **options):

        fetch_queue = []

        if options.get('toplist'):
            for e in models.ToplistEntry.objects.all().order_by('-subscriptions')[:100]:
                fetch_queue.append(e.podcast)

        if options.get('new'):
            podcasts = models.Podcast.objects.filter(episode__title='', episode__outdated=False).distinct()
            fetch_queue.extend(podcasts)

        for url in args:
           try:
                fetch_queue.append(models.Podcast.objects.get(url=url))
           except:
                pass

        if len(fetch_queue) == 0 and not options.get('toplist') and not options.get('new'):
            fetch_queue = models.Podcast.objects.filter(last_update__lt=UPDATE_LIMIT)

        if options.get('list'):
            print '%d podcasts would be updated' % len(fetch_queue)
            print '\n'.join([p.url for p in fetch_queue])

        else:
            print 'Updating %d podcasts...' % len(fetch_queue)
            feeddownloader.update_podcasts(fetch_queue)
