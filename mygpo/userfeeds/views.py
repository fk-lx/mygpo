from django.shortcuts import render
from django.contrib.sites.models import RequestSite
from django.http import Http404

from mygpo.userfeeds.auth import require_token_auth
from mygpo.userfeeds.feeds import FavoriteFeed
from mygpo.users.models import User


@require_token_auth('favorite_feeds_token')
def favorite_feed(request, username):

    site = RequestSite(request)

    user = User.get_user(username)
    if not user:
        raise Http404

    feed = FavoriteFeed(user)

    return render(request, 'userfeed.xml', {
        'site': site,
        'feed_user': user,
        'feed': feed,
        }, content_type='text/xml')
