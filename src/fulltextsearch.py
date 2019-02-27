#!/usr/bin/env python

'''
arxivdb - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jun 2014

Contains utilities for astroph-coffee server SQLite database manipulation for
inserting/modifying arXiv papers.

'''

try:
    from pysqlite2 import dbapi2 as sqlite3
except Exception as e:
    print("can't find internal pysqlite2, falling back to Python sqlite3 "
          "full-text search may not work right "
          "if your sqlite3.sqlite3_version is old (< 3.8.6 or so)")
    import sqlite3

import ConfigParser
import array
import math
import numpy as np


CONF = ConfigParser.ConfigParser()
CONF.read('conf/astroph.conf')

DBPATH = CONF.get('sqlite3','database')

# local imports
from arxivdb import opendb


FTS_COLUMNS = ['utcdate',
               'day_serial',
               'title',
               'article_type',
               'arxiv_id',
               'authors',
               'abstract',
               'link',
               'pdf',
               'nvotes',
               'local_authors']


def get_matchinfo_arrays(matchinfo_rows):
    '''
    This justs unpacks the blob returned by sqlite3 matchinfo function.

    this is run on the matchinfo rows returned by a query like so:

    select ...cols...,matchinfo(arxiv_fts,'pcxnal') from arxiv_fts where ...

    Pass in the matchinfo... values to this function.

    '''

    matchinfo_arrays = []

    for row in matchinfo_rows:

        this_arr = array.array('I')
        this_row_str = str(row)
        this_arr.fromstring(this_row_str)

        matchinfo_arrays.append(this_arr)

    return matchinfo_arrays



def okapi_bm25(matchinfo_array, search_column, k1=1.2, b=0.75):
    '''
    This calculates the relevance using the Okapi BM25 algorithm.

        https://en.wikipedia.org/wiki/Okapi_BM25

    We'd ordinarily use the built-in version, but FTS5 doesn't work on older
    sqlite3 installations we're stuck with on CentOS 7.

    Use this on a single matchinfo array returned by get_matchinfo_arrays.

    This is a pretty straightforward copy of the okapi_bm25 function in:

    https://github.com/neozenith/sqlite-okapi-bm25/blob/master/okapi_bm25.c

    '''

    if search_column not in FTS_COLUMNS:
        print("unknown column, can't calculate bm25 for %s" % search_column)
        return 0.0
    else:
        searchTextCol = FTS_COLUMNS.index(search_column)

    P_OFFSET = 0
    C_OFFSET = 1
    X_OFFSET = 2

    termCount = matchinfo_array[P_OFFSET]
    colCount = matchinfo_array[C_OFFSET]

    N_OFFSET = X_OFFSET + 3*termCount*colCount
    A_OFFSET = N_OFFSET + 1
    L_OFFSET = (A_OFFSET + colCount)

    totalDocs = matchinfo_array[N_OFFSET]
    avgLength = matchinfo_array[A_OFFSET + searchTextCol]
    docLength = matchinfo_array[L_OFFSET + searchTextCol]

    sum = 0.0

    for ind in range(termCount):

        # this calculation for currentX is incorrect, according to:
        # - https://github.com/rads/sqlite-okapi-bm25/issues/2
        # - https://github.com/coleifer/peewee/issues/1826#issuecomment-451780948
        # I noticed this here:
        # https://simonwillison.net/2019/Jan/7/exploring-search-relevance-algorithms-sqlite/
        # currentX = X_OFFSET + (3 * searchTextCol * (ind + 1))

        # this should be the correct value of currentX
        currentX = X_OFFSET + (3 * (searchTextCol + ind*colCount))

        termFrequency = matchinfo_array[currentX]
        docsWithTerm = matchinfo_array[currentX + 2]

        idf = math.log(
            (totalDocs - docsWithTerm + 0.5) /
            (docsWithTerm + 0.5)
        )

        rightSide = (
            (termFrequency * (k1 + 1)) /
            (termFrequency + (k1 * (1 - b + (b * (docLength / avgLength)))))
        )

        sum += (idf * rightSide)

    return sum



def okapi_bm25_values(matchinfo_rows, search_column, k1=1.2, b=0.75):
    '''This calculates the relevance using the Okapi BM25 algorithm.

        https://en.wikipedia.org/wiki/Okapi_BM25

    Inspired by:
    - https://github.com/neozenith/sqlite-okapi-bm25/blob/master/okapi_bm25.c
    - https://sqlite.org/fts5.html#the_bm25_function

    We'd ordinarily use the built-in version, but FTS5 doesn't work on older
    sqlite3 installations we're stuck with on CentOS 7.

    This is used on the results of the matchinfo FTS4 function called like so:

    matchinfo(arxiv_fts,'pcxnal');

    k1 and b are free parameters to tune the function.

    k1 = 1.2
    b = 0.75

    are good starting values. See the wikipedia page for more info.

    NOTE: this doesn't work with FTS5 tables. There's no matchinfo function any
    more.

    '''

    # get the arrays from the rows
    matchinfo_arrs = get_matchinfo_arrays(matchinfo_rows)

    # get the bm25 values
    bm25_vals = [okapi_bm25(x, search_column, k1=k1, b=b)
                 for x in matchinfo_arrs]

    return bm25_vals



def fts4_phrase_query_paginated(querystr,
                                getcolumns,
                                sortcol='utcdate',
                                sortorder='desc',
                                pagelimit=100,
                                pagestarter=None,
                                bm25_k1=1.2,
                                bm25_b=0.75,
                                relevance_weights=None,
                                database=None):
    '''This just runs the verbatim query querystr on the full FTS4 table.

    getcolumns is a list of column names to return from the arxiv table.

    sortcol is either a string indicating a column in the arxiv table to use for
    sorting the match results or a string == 'relevance'. If sortcol is
    'relevance', results will be returned in sortorder order sorted by Okapi
    BM25 relevance.

    https://en.wikipedia.org/wiki/Okapi_BM25

    sortorder is either 'asc' for ascending order, or 'desc' for descending
    order.

    pagelimit is an integer number of elements to return. This is a 'page' of
    results.

    pagestarter is the last element in the sorted values of sortcol returned by
    a previous run of this function. This is used to figure out where the next
    page should start. Elements after pagestarter in sortorder order in sortcol
    are returned for the next page.

    Returns a dict of the following form:

    {'nmatches','results','columns','sortcol','sortorder','pagelimit'}

    'results' is a dict containing all the results with the keys as the
    requested getcolumns and the values as sorted elements in sortorder using
    the sortcol.

    We calculate the overall rank by calculating a weighted average for
    bm25(title), bm25(abstract), bm25(authors) using relevance_weights. These
    should be probably set appropriately for the type of query.

    NOTE: this does not work with fts5 tables, since there's no matchinfo
    returned. on the other hand, fts5 provides a native bm25 and sort ordering
    is way more straightforward.

    FIXME: add the okapi_bm25f weighted function here later. this will allow us
    to weight individual fields better.

    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False

    # this is the usual sort order without relevance
    if sortcol != 'relevance':

        # add the sortcol to the query so we can paginate on it later
        if sortcol not in getcolumns:
            getcolumns.insert(0,sortcol)

        columnstr = ',' .join(['arxiv.%s' % x for x in getcolumns])

        # this does paging
        # pagestarter is the last element in the sortcol of the previous results
        # pageop is chosen based on sortorder: > if 'asc', < if 'desc'
        if pagestarter:

            if sortorder == 'asc':
                pageop = '>'
            else:
                pageop = '<'

            query = ('select {columns} from '
                     'arxiv_fts join arxiv on (arxiv_fts.docid = arxiv.rowid) '
                     'where arxiv_fts MATCH ? and '
                     'arxiv.{sortcol} {pageop} ? '
                     'order by arxiv_fts.{sortcol} {sortorder}')
            query = query.format(columns=columnstr,
                                 sortcol=sortcol,
                                 pageop=pageop,
                                 pagestarter=pagestarter,
                                 sortorder=sortorder)
            queryparams = (querystr, pagestarter)

        else:

            query = ('select {columns} from '
                     'arxiv_fts join arxiv on (arxiv_fts.docid = arxiv.rowid) '
                     'where arxiv_fts MATCH ? '
                     'order by arxiv_fts.{sortcol} {sortorder}')
            query = query.format(columns=columnstr,
                                 sortcol=sortcol,
                                 sortorder=sortorder)
            queryparams = (querystr,)


        # use page limit if necessary
        if pagelimit and pagelimit > 0:
            query = '%s limit %s' % (query, pagelimit)
        else:
            pagelimit = 100
            query = '%s limit %s' % (query, pagelimit)

        print(query, queryparams)

        cursor.execute(query, queryparams)
        rows = cursor.fetchall()

        nmatches = len(rows)

        if nmatches > 0:
            mcols = zip(*rows)
            results = {x:y for x,y in zip(getcolumns, mcols)}
        else:
            results = None


    # otherwise, we need to do some special stuff for relevance sortorder
    else:

        # we'll sort in desc relevance order, so we ignore the usual sortorder
        columnstr = ',' .join(['arxiv.%s' % x for x in getcolumns])

        queryparams = []

        # first, let's handle queries with no pagestarter given
        if not pagestarter:

            # generate the query
            query = ("select {columns}, "
                     "matchinfo(arxiv_fts,'pcxnal') as minfo from "
                     "arxiv_fts join arxiv on (arxiv_fts.docid = arxiv.rowid) "
                     "where arxiv_fts MATCH ?")
            query = query.format(columns=columnstr)
            queryparams = (querystr,)

            print(query, queryparams)

            cursor.execute(query, queryparams)
            rows = cursor.fetchall()

            nmatches = len(rows)

            # if we have matches, we can process ranks and sort orders
            if nmatches > 0:

                # add the matchinfo column at the end for correct zipping
                getcolumns.append('minfo')

                mcols = zip(*rows)
                results = {x:y for x,y in zip(getcolumns, mcols)}

                # calculate the ranks for the abstract, title, and authors
                abstract_bm25 = np.array(okapi_bm25_values(results['minfo'],
                                                           'abstract',
                                                           k1=bm25_k1,
                                                           b=bm25_b))
                title_bm25 = np.array(okapi_bm25_values(results['minfo'],
                                                        'title',
                                                        k1=bm25_k1,
                                                        b=bm25_b))
                authors_bm25 = np.array(okapi_bm25_values(results['minfo'],
                                                          'authors',
                                                          k1=bm25_k1,
                                                          b=bm25_b))

                # weight the ranks
                _bm25 = np.column_stack((title_bm25,
                                         abstract_bm25,
                                         authors_bm25))

                # weighted average of bm25
                overall_bm25 = np.average(_bm25,
                                          axis=1,
                                          weights=relevance_weights)

                # now sort by weighted sum
                bm25_order = np.argsort(overall_bm25)[::-1]

                overall_bm25 = overall_bm25[bm25_order]
                title_bm25 = title_bm25[bm25_order]
                abstract_bm25 = abstract_bm25[bm25_order]
                authors_bm25 = authors_bm25[bm25_order]

                # resort all the columns in bm25 order
                # (except the last one which is minfo)
                # here we also do the pagination
                for colx in getcolumns[:-1]:

                    results[colx] = np.array(results[colx])[bm25_order]
                    if pagelimit and pagelimit > 0:
                        results[colx] = results[colx][:pagelimit]
                    results[colx] = results[colx].tolist()

                # get rid of the matchinfo stuff now that we don't need it
                del results['minfo']

                # add the bm25's to the dict
                results['abstract_bm25'] = abstract_bm25[:pagelimit]
                results['title_bm25'] = title_bm25[:pagelimit]
                results['authors_bm25'] = authors_bm25[:pagelimit]
                results['overall_bm25'] = overall_bm25[:pagelimit]

            # if no matches, no need to do anything
            else:
                results = None

        # if there is a page starter, then it's a previous overall_bm25 value
        # get everything below that value
        else:

            # generate the query
            query = ("select {columns}, "
                     "matchinfo(arxiv_fts,'pcxnal') as minfo from "
                     "arxiv_fts join arxiv on (arxiv_fts.docid = arxiv.rowid) "
                     "where arxiv_fts MATCH ?")
            query = query.format(columns=columnstr)
            queryparams = (querystr,)

            print(query, queryparams)

            cursor.execute(query, queryparams)
            rows = cursor.fetchall()

            nmatches = len(rows)

            # if we have matches, we can process ranks and sort orders
            if nmatches > 0:

                # add the matchinfo column at the end for correct zipping
                getcolumns.append('minfo')

                mcols = zip(*rows)
                results = {x:y for x,y in zip(getcolumns, mcols)}

                # calculate the ranks for the abstract, title, and authors
                abstract_bm25 = np.array(okapi_bm25_values(results['minfo'],
                                                           'abstract',
                                                           k1=bm25_k1,
                                                           b=bm25_b))
                title_bm25 = np.array(okapi_bm25_values(results['minfo'],
                                                        'title',
                                                        k1=bm25_k1,
                                                        b=bm25_b))
                authors_bm25 = np.array(okapi_bm25_values(results['minfo'],
                                                          'authors',
                                                          k1=bm25_k1,
                                                          b=bm25_b))

                # weight the ranks
                _bm25 = np.column_stack((title_bm25,
                                         abstract_bm25,
                                         authors_bm25))

                # weighted sum
                overall_bm25 = np.average(_bm25,
                                          axis=1,
                                          weights=relevance_weights)

                # now sort by weighted sum
                bm25_order = np.argsort(overall_bm25)[::-1]

                overall_bm25 = overall_bm25[bm25_order]
                title_bm25 = title_bm25[bm25_order]
                abstract_bm25 = abstract_bm25[bm25_order]
                authors_bm25 = authors_bm25[bm25_order]

                # get bm25 < pagestart indices
                thispage_bm25_ind = np.where(overall_bm25 < pagestarter)

                # resort all the columns in bm25 order
                # (except the last one which is minfo)
                # here we also do the pagination
                for colx in getcolumns[:-1]:

                    results[colx] = np.array(results[colx])[bm25_order]

                    # get stuff below pagestarter
                    results[colx] = results[colx][thispage_bm25_ind]

                    if pagelimit and pagelimit > 0:
                        results[colx] = results[colx][:pagelimit]
                    results[colx] = results[colx].tolist()

                # get rid of the matchinfo stuff now that we don't need it
                del results['minfo']

                # add the bm25's to the dict

                results['abstract_bm25'] = (
                    abstract_bm25[thispage_bm25_ind][:pagelimit]
                )
                results['title_bm25'] = (
                    title_bm25[thispage_bm25_ind][:pagelimit]
                )
                results['authors_bm25'] = (
                    authors_bm25[thispage_bm25_ind][:pagelimit]
                )
                results['overall_bm25'] = (
                    overall_bm25[thispage_bm25_ind][:pagelimit]
                )

            # if no matches, no need to do anything
            else:
                results = None


    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()

    return {'nmatches':nmatches,
            'results':results,
            'columns':getcolumns,
            'sortcol':sortcol,
            'sortorder':sortorder,
            'pagelimit':pagelimit}



def column_simple_query(querystr,
                        matchcolumn,
                        getcolumns,
                        database=None):
    '''This runs the MATCH querystr against matchcolumn only and returns
    getcolumns.

    getcolumns are columns in the arxiv_fts table to return. getcolumns is a
    list of strings with column names.

    '''

    # open the database if needed and get a cursor
    if not database:
        database, cursor = opendb()
        closedb = True
    else:
        cursor = database.cursor()
        closedb = False

    columnstr = ',' .join(getcolumns)
    query = 'select {columns} from arxiv_fts where {matchcol} MATCH ?'
    query = query.format(columnstr=columnstr, matchcol=matchcolumn)

    cursor.execute(query, (querystr,))
    rows = cursor.fetchall()

    # at the end, close the cursor and DB connection
    if closedb:
        cursor.close()
        database.close()

    return rows
