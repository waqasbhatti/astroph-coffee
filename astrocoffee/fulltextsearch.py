# -*- coding: utf-8 -*-

'''This contains FTS5 search functions for coffeeserver.

'''

#############
## LOGGING ##
#############

import logging
LOGGER = logging.getLogger(__name__)

LOGDEBUG = LOGGER.debug
LOGINFO = LOGGER.info
LOGWARNING = LOGGER.warning
LOGERROR = LOGGER.error
LOGEXCEPTION = LOGGER.exception


#############
## IMPORTS ##
#############

import sqlite3
import copy


############
## CONFIG ##
############

# the columns available for search and their default relevance weights
FTS_COLUMNS = {
    'utcdate':1.0,
    'title':4.0,
    'arxiv_id':1.0,
    'authors':5.0,
    'abstract':3.0,
}


###################
## FTS FUNCTIONS ##
###################

def full_text_query(
        connection,
        query_string,
        columns,
        column_weights=None,
        max_rows=500,
        start_relevance=None,
):
    '''This runs an FTS query.

    This requires an active SQLite DBAPI connection. Get this from the
    SQLAlchemy Connection.connection object.

    '''

    # this is the query to run
    q = ("select arxiv_fts.rowid, {column_string}, arxiv_fts.rank as relevance "
         "from arxiv_fts join arxiv_listings "
         "on (arxiv_fts.rowid = arxiv_listings.rowid) where "
         "arxiv_fts MATCH ? "
         "{condition_string}"
         "order by bm25(arxiv_fts{relevance_weights})"
         "{limit_string}")

    query_cols = list(set(FTS_COLUMNS.keys()) & set(columns))

    if len(query_cols) == 0:
        LOGERROR("All requested query columns are unavailable: %r" % columns)
        return None

    column_str = ', '.join('arxiv_listings.%s' % x for x in query_cols)

    if column_weights is not None and len(column_weights) == len(query_cols):
        relevance_weights = (
            ', %s' % ', '.join('%.1f' % x for x in column_weights)
        )
    else:
        relevance_weights = ', %s' % ', '.join(
            '%.1f' % FTS_COLUMNS[x] for x in query_cols
        )

    query_params = [query_string]

    # handle the limit string
    if max_rows is not None:
        limit_string = ' limit %s' % max_rows
    else:
        limit_string = ''

    # handle the start rank (useful for pagination)
    if start_relevance is not None:
        condition_string = ' where arxiv_fts.rank > ? '
        query_params.append(start_relevance)
    else:
        condition_string = ''

    q = q.format(
        column_string=column_str,
        relevance_weights=relevance_weights,
        limit_string=limit_string,
        condition_string=condition_string
    )
    LOGINFO(
        "Executing FTS query: '%s' and fetching columns: %s with weights: %s" %
        (query_string, column_str, relevance_weights.lstrip(', '))
    )

    existing_row_factory = copy.deepcopy(connection.row_factory)

    try:

        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(q, tuple(query_params))
        rows = cursor.fetchall()
        cursor.close()

    except Exception:

        LOGEXCEPTION(
            "Could not execute FTS query: '%s'" % query_string
        )
        rows = []

    finally:

        connection.row_factory = existing_row_factory

    if len(rows) > 0:
        top_relevance = rows[0][-1]
        last_relevance = rows[-1][-1]
    else:
        top_relevance = 0
        last_relevance = 0

    return {'result':rows,
            'nrows':len(rows),
            'columns':['rowid'] + query_cols + ['relevance'],
            'weights':relevance_weights,
            'query':q,
            'top_relevance':top_relevance,
            'last_relevance':last_relevance}
