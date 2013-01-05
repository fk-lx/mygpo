import collections
import urlparse
import re

from django.core.cache import cache

from mygpo.core import models
from mygpo.log import log
from mygpo.utils import iterate_together, progress
from mygpo.db.couchdb.podcast import podcast_count, podcast_for_oldid, \
        all_podcasts
from mygpo.db.couchdb.common import sanitizingrules_by_obj_type


def sanitize_urls(urls, obj_type='podcast'):
    """ Apply sanitizing rules to the given URLs and return the results """

    return [sanitize_url(url, obj_type) for url in urls]


def sanitize_url(url, obj_type='podcast'):
    """ Apply sanitizing rules to the given URL and return the results """

    rules = sanitizingrules_by_obj_type(obj_type)
    url = basic_sanitizing(url)
    url = apply_sanitizing_rules(url, rules)
    return url



def basic_sanitizing(url):
    """
    does basic sanitizing through urlparse and additionally converts the netloc to lowercase
    """
    r = urlparse.urlsplit(url)
    netloc = r.netloc.lower()
    r2 = urlparse.SplitResult(r.scheme, netloc, r.path, r.query, '')
    return r2.geturl()


def apply_sanitizing_rules(url, rules):
    """
    applies all url sanitizing rules to the given url
    setting podcast=True uses only those rules which have use_podcast set to True.
    When passing podcast=False this check is ommitted. The same is valid
    for episode.
    """

    for rule in rules:

        orig = url

        # check for precompiled regex first
        if hasattr(rule, 'search_re'):
            url = rule.search_re.sub(rule.replace, url)
        else:
            url = re.sub(rule.search, rule.replace, url)

        if orig != url:
            c = getattr(rule, 'hits', 0)
            rule.hits = c+1

    return url


def maintenance(dry_run=False):
    """
    This currently checks how many podcasts could be removed by
    applying both basic sanitizing rules and those from the database.

    This will later be used to replace podcasts!
    """

    podcast_rules = sanitizingrules_by_obj_type('podcast')
    episode_rules = sanitizingrules_by_obj_type('episode')

    num_podcasts = podcast_count()

    print 'Stats'
    print ' * %d podcasts - %d rules' % (num_podcasts, len(podcast_rules))
    if dry_run:
        print ' * dry run - nothing will be written to the database'
    print

    print 'precompiling regular expressions'

    podcast_rules = list(precompile_rules(podcast_rules))
    episode_rules = list(precompile_rules(episode_rules))

    p_stats = collections.defaultdict(int)
    e_stats = collections.defaultdict(int)

    podcasts = all_podcasts()

    for n, p in enumerate(podcasts):
        su = sanitize_url(p.url, rules=podcast_rules)

        # nothing to do
        if su == p.url:
            p_stats['unchanged'] += 1
            continue

        # invalid podcast, remove
        if su == '':
            if not dry_run:
                p.delete()
            p_stats['deleted'] += 1

        su_podcast = podcast_for_url(url=su)

        if not su_podcast:
            # "target" podcast does not exist, we simply change the url
            if not dry_run:
                log('updating podcast %s - "%s" => "%s"' % (p.id, p.url, su))
                p.url = su
                p.save()

            p_stats['updated'] += 1
            continue

        # nothing to do
        if p == su_podcast:
            p_stats['unchanged'] += 1
            continue

        # last option - merge podcasts
        if not dry_run:
            rewrite_podcasts(p, su_podcast)
            p.delete()

        p_stats['merged'] += 1

        progress(n+1, num_podcasts, str(p.id))

    print 'finished %s podcasts' % (n+1)
    print '%(unchanged)d unchanged, %(merged)d merged, %(updated)d updated, %(deleted)d deleted, %(error)d error' % p_stats
    print 'Hits'
    for _, r in podcast_rules:
        print '% 30s: %d' % (r.slug, getattr(r, 'hits', 0) if hasattr(r, 'hits') else 0)


def rewrite_podcasts(p_old, p_new):

    log('merging podcast %s "%s" to correct podcast %s "%s"' % (p_old.id, p_old.url, p_new.id, p_new.url))

    rewrite_newpodcast(p_old, p_new)

def rewrite_newpodcast(p_old, p_new):
    p_n = podcast_for_oldid(p_new.id)
    p_o = podcast_for_oldid(p_old.id)

    if None in (p_n, p_o):
        return


    # merge subscriber data
    subscribers = []
    compare = lambda a, b: cmp(a.timestamp, b.timestamp)
    for n, o in iterate_together([p_n.subscribers, p_o.subscribers]):

        # we assume that the new podcast has much more subscribers
        # taking only count of the old podcast would look like a drop
        if None in (n, o):
            continue

        subscribers.append(
                models.SubscriberData(
                    timestamp = o.timestamp,
                    subscriber_count = n.subscriber_count + \
                                       n.subscriber_count if n else 0\
                )
            )

    p_n.subscribers = subscribers

    p_n.save()
    p_o.delete()


def precompile_rules(rules):
    for rule in rules:
        rule.search_re = re.compile(rule.search, re.UNICODE)
        yield rule
