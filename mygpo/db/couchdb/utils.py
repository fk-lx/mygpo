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

import os.path
import operator
import string
import functools

from couchdbkit.loaders import FileSystemDocsLoader
from couchdbkit.ext.django import loading

from django.conf import settings

from mygpo.db.couchdb import get_main_database

import logging
logger = logging.getLogger(__name__)


def multi_request_view(cls, view, wrap=True, auto_advance=True,
        *args, **kwargs):
    """
    splits up a view request into several requests, which reduces
    the server load of the number of returned objects is large.

    NOTE: As such a split request is obviously not atomical anymore, results
    might skip some elements of contain some twice

    If auto_advance is False the method will always request the same range.
    This can be useful when the view contain unprocessed items and the caller
    processes the items, thus removing them from the view before the next
    request.
    """

    per_page = kwargs.get('limit', 1000)
    kwargs['limit'] = per_page + 1
    db = get_main_database()
    wrapper = kwargs.pop('wrapper', False) or cls.wrap
    cont = True

    while cont:

        resp = db.view(view, *args, **kwargs)
        cont = False

        for n, obj in enumerate(resp.iterator()):

            key = obj['key']

            if wrap:
                doc = wrapper(obj['doc']) if wrapper else obj['doc']
                docid = doc._id if wrapper else obj['id']
            else:
                docid = obj.get('id', None)
                doc = obj

            if n == per_page:
                if auto_advance:
                    kwargs['startkey'] = key
                    if docid is not None:
                        kwargs['startkey_docid'] = docid
                    if 'skip' in kwargs:
                        del kwargs['skip']

                # we reached the end of the page, load next one
                cont = True
                break

            yield doc



def is_couchdb_id(id_str):
    f = functools.partial(operator.contains, string.hexdigits)
    return len(id_str) == 32 and all(map(f, id_str))


def sync_design_docs():
    """ synchronize the design docs for all databases """

    base_dir = settings.BASE_DIR

    for part, label in settings.COUCHDB_DDOC_MAPPING.items():
            path = os.path.join(base_dir, '..', 'couchdb', part, '_design')

            logger.info('syncing ddocs for "%s" from "%s"', label, path)

            db = loading.get_db(label)
            loader = FileSystemDocsLoader(path)
            loader.sync(db, verbose=True)


def view_cleanup():
    """ do a view-cleanup for all databases """

    logger.info('Doing view cleanup for all databases')
    for label in settings.COUCHDB_DDOC_MAPPING.values():
        logger.info('Doing view cleanup for database "%s"', label)
        db = loading.get_db(label)
        res = db.view_cleanup()

        if res.get('ok', False):
            log = logger.info
        else:
            log = logger.warn

        log('Result of view cleanup for database "%s": %s', label, res)
