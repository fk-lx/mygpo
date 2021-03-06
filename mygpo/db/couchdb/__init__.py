import itertools

from operator import itemgetter
from collections import namedtuple

from couchdbkit.ext.django import loading
from couchdbkit import MultipleResultsFound
from couchdbkit import *

from mygpo.utils import split_quoted

import logging
logger = logging.getLogger(__name__)


def get_main_database():
    return loading.get_db('core')


def get_categories_database():
    """ returns the database that contains Category documents """
    return loading.get_db('categories')


def get_pubsub_database():
    return loading.get_db('pubsub')


def get_userdata_database():
    return loading.get_db('userdata')

def get_database(user=None):
    return get_main_database()


class BulkException(Exception):

    def __init__(self, errors):
        self.errors = errors


BulkError = namedtuple('BulkError', 'doc error reason')


def __default_reload(db, obj):
    doc = db[obj._id]
    return obj.__class__.wrap(doc)


__get_obj = itemgetter(0)

def bulk_save_retry(obj_funs, db, reload_f=__default_reload):
    """ Saves multiple documents and retries failed ones

    Objects to be saved are passed as (obj, mod_f), where obj is the CouchDB
    and mod_f is the modification function that should be applied to it.

    If saving a document fails, it is again fetched from the database, the
    modification function is applied again and saving is retried. """

    errors = []

    while True:

        # apply modification function (and keep funs)
        obj_funs = [(f(o), f) for (o, f) in obj_funs]

        # filter those with obj None
        obj_funs = filter(lambda of: __get_obj(of) is not None, obj_funs)

        # extract objects
        objs = map(__get_obj, obj_funs)

        if not objs:
            return

        try:
            db.save_docs(objs)
            return

        except BulkSaveError as ex:

            new_obj_funs = []
            for res, (obj, f) in zip(ex.results, obj_funs):
                if res.get('error', False) == 'conflict':

                    # reload conflicted object
                    obj = reload_f(db, obj)
                    new_obj_funs.append( (obj, f) )

                elif res.get('error', False):
                    # don't retry other errors
                    err = BulkError(obj, res['error'], res.get('reason', None))
                    errors.append(err)

            obj_funs = new_obj_funs

    if errors:
        logger.warn('Errors at bulk-save: %s', errors)
        raise BulkException(errors)


def lucene_query(fields, query_str):
    """ returns a Lucene query string for the given fields and query string

    >>> lucene_query(['title'], 'podcast show')
    'title:"podcast" OR title:"show"'

    >>> lucene_query(['a', 'b'], '"x y"')
    'a:"x y" OR b:"x y"'
    """

    keywords = split_quoted(query_str)

    # search all keywords in all fields
    criteria = itertools.product(fields, keywords)

    # build query str for each criterion
    criteria_str = ['{field}:"{q}"'.format(field=f, q=q) for f, q in criteria]

    # combine all with OR
    return ' OR '.join(criteria_str)


def get_single_result(db, view, **query_args):
    """ return a single CouchDB view result

    Logs an error if multiple results are returned, and uses the first result.
    This can happen as CouchDB can not guarantee uniqueness of attributes other
    than _id. If no result are fetched, None is returned. """

    r = db.view(view, **query_args)

    if not r:
        return None

    try:
        result = r.one()

    except MultipleResultsFound as ex:
        logger.exception('Multiple results found in %s with params %s',
                         view, query_args)
        # use the first result as fallback
        result = r.first()

    # we can only set the db if the result has been
    # wrapped (depending on query_args)
    if hasattr(result, 'set_db'):
        result.set_db(db)

    return result
