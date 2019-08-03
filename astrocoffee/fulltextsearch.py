# -*- coding: utf-8 -*-

'''This contains FTS5 search functions for coffeeserver.

'''

#############
## LOGGING ##
#############

import logging
from astrocoffee import log_sub, log_fmt, log_date_fmt
LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    style=log_sub,
    format=log_fmt,
    datefmt=log_date_fmt,
)

LOGDEBUG = LOGGER.debug
LOGINFO = LOGGER.info
LOGWARNING = LOGGER.warning
LOGERROR = LOGGER.error
LOGEXCEPTION = LOGGER.exception


############
## CONFIG ##
############

# the columns available for search, their default relevance weights, and their
# column numbers in the arxiv_fts table.
FTS_COLUMNS = {
    'utcdate':{'weight':1.0, 'column':0},
    'title':{'weight':4.0, 'column':1},
    'arxiv_id':{'weight':1.0,'column':3},
    'authors':{'weight':5.0,'column':4},
    'abstract':{'weight':3.0,'column':5},
    'link':{'weight':0.0,'column':6},
    'pdf':{'weight':0.0,'column':7},
    'voter_info':{'weight':0.0,'column':8},
    'presenter_info':{'weight':0.0,'column':9},
    'reserver_info':{'weight':0.0,'column':10},
}


###################
## FTS FUNCTIONS ##
###################

def full_text_query(
        connection,
        query_string,
        columns=(
            'utcdate',
            'title',
            'arxiv_id',
            'authors',
            'abstract',
            'link',
            'pdf',
            'voter_info',
            'presenter_info',
            'reserver_info',
        ),
        column_weights=None,
        max_rows=500,
        start_relevance=None,
        highlight=(
            'title',
            'authors',
            'abstract'
        )
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

    # get the valid query columns
    query_cols = list(set(FTS_COLUMNS.keys()) & set(columns))

    if len(query_cols) == 0:
        LOGERROR("All requested query columns are unavailable: %r" % columns)
        return None

    # format the query columns
    query_col_list = query_cols[::]
    query_cols = ['arxiv_listings.%s' % x for x in query_col_list]
    highlight_col_list = []

    # handle any highlight requests
    if highlight is not None:

        highlight_str = """\
highlight(arxiv_fts, %s, '<span>','</span>')"""

        for hcol in highlight:
            query_cols.append(highlight_str % FTS_COLUMNS[hcol]['column'])
            highlight_col_list.append('%s_highlight' % hcol)

    # put together all the columns into a column string
    column_str = ', '.join(x for x in query_cols)

    if (column_weights is not None and
        len(column_weights) == len(query_col_list)):
        relevance_weights = (
            ', %s' % ', '.join('%.1f' % x for x in column_weights)
        )
    else:
        relevance_weights = ', %s' % ', '.join(
            '%.1f' % FTS_COLUMNS[x]['weight'] for x in query_col_list
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

    try:

        cursor = connection.cursor()
        cursor.execute(q, tuple(query_params))
        rows = cursor.fetchall()
        cursor.close()

    except Exception:

        LOGEXCEPTION(
            "Could not execute FTS query: '%s'" % query_string
        )
        rows = []

    if len(rows) > 0:
        top_relevance = rows[0][-1]
        last_relevance = rows[-1][-1]
    else:
        top_relevance = 0
        last_relevance = 0

    return {'result':rows,
            'nmatches':len(rows),
            'columns':(['rowid'] + query_col_list +
                       highlight_col_list + ['relevance']),
            'weights':{
                x:float(y) for x,y in
                zip(query_col_list, relevance_weights.lstrip(', ').split(','))
            },
            'query':q,
            'top_relevance':top_relevance,
            'last_relevance':last_relevance}
