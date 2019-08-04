# -*- coding: utf-8 -*-

'''This handles author-related operations.

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


#############
## IMPORTS ##
#############

import re
import csv

from dateutil import parser
from tornado.escape import squeeze
from fuzzywuzzy import process
from sqlalchemy import select, update, insert, exc, delete

from . import database


###############
## CONSTANTS ##
###############

# to get rid of parens in author names
# these are applied in order

# this should turn:
# "author1 (1, 2, & 3), author1 (1, 2, and 3), ((1) blah1, (2) blah2)"
# into:
# "author1, author2"
affil_regex1 = re.compile(r'\([0-9, &and]+\)')

# this gets rid of patterns like (blah)
affil_regex2 = re.compile(r'\([^)]*\)')

# this gets rid of patterns like (blah)
affil_regex3 = re.compile(r'\(\w+|\s+\)')


#######################
## UTILITY FUNCTIONS ##
#######################

def strip_affiliations(authorstr, subchar=','):
    '''
    This tries to strip author affils from authorstr.

    As far as I can test, I think this handles:

    author (affil, ...)
    author (1) ... ((1) affil, ....)
    author (1, 2) ... ((1) affil, ....)
    author (1 & 2) ... ((1) affil, ....)
    author (1 and 2) ... ((1) affil, ....)

    I don't think it can handle:

    author (1) ... (1) affil, ...

    but I haven't seen these in use (yet).

    '''

    initial = authorstr.replace("Authors: ","")
    initial = authorstr.replace('\n','')
    prelim = affil_regex1.sub(subchar, initial)
    intermed1 = affil_regex2.sub(subchar, prelim)
    intermed2 = affil_regex3.sub(subchar, intermed1)
    cleaned = intermed2.split(',')
    final = [squeeze(x.strip()) for x in cleaned if len(x) > 1]

    return final


###################################
## INSERTING AUTHORS INTO THE DB ##
###################################

def insert_local_authors(
        dbinfo,
        author_csv,
        dbkwargs=None,
        truncate=False,
        overwrite=True,
):
    '''This inserts local authors into the database.

    author_csv is a CSV file with three columns:

    author_name, author_email, author_special_affiliation

    author_special_affiliation can be an empty string to indicate the author is
    associated with the main group of people that'll be using the server. If the
    author belongs to another institution but should be counted as a local
    author, include that institution's name here.

    truncate = True will clear the table before adding the authors. Useful for
    start-of-year updates.

    overwrite = True will update existing items.

    '''

    #
    # get the database
    #
    dbref, dbmeta = dbinfo
    if not dbkwargs:
        dbkwargs = {}
    if isinstance(dbref, str):
        engine, conn, meta = database.get_astrocoffee_db(dbref,
                                                         dbmeta,
                                                         **dbkwargs)
    else:
        engine, conn, meta = None, dbref, dbmeta
        meta.bind = conn

    #
    # actual work
    #

    local_authors = meta.tables['local_authors']

    # read the CSV
    csvfd = open(author_csv,'r')

    with conn.begin() as transaction:

        if truncate:
            LOGWARNING("Deleting all existing local authors.")
            delall = delete(local_authors)
            conn.execute(delall)

        LOGINFO("Inserting local authors...")

        ins = insert(local_authors)

        csvreader = csv.DictReader(
            csvfd,
            fieldnames=('name','email', 'affiliation')
        )

        for row in csvreader:

            affiliation = row['affiliation']
            if len(affiliation) == 0:
                affiliation = None

            info = {
                'affiliation':row['affiliation'],
                'server_user_id':None,
                'server_user_role':None
            }

            try:

                conn.execute(
                    ins,
                    name=row['name'],
                    email=row['email'],
                    info=info
                )

            except exc.IntegrityError:

                transaction.rollback()

                if not overwrite:
                    LOGERROR(
                        "Author: %s with email: %s already exists "
                        "in the DB and overwrite=False. Skipping..."
                        % (row['name'], row['email'])
                    )
                    continue

                upd = update(local_authors).where(
                    local_authors.c.name == row['name']
                ).values(
                    name=row['name'],
                    email=row['email'],
                    info=info
                )

                conn.execute(upd)
                LOGWARNING("Updated existing author info for author: %s" %
                           row['name'])
    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    #
    # close the CSV
    #
    csvfd.close()


def add_local_author(
        dbinfo,
        name,
        email,
        affiliation=None,
        dbkwargs=None,
        overwrite=True,
):
    '''
    This inserts a single local author into the database.

    '''

    #
    # get the database
    #
    dbref, dbmeta = dbinfo
    if not dbkwargs:
        dbkwargs = {}
    if isinstance(dbref, str):
        engine, conn, meta = database.get_astrocoffee_db(dbref,
                                                         dbmeta,
                                                         **dbkwargs)
    else:
        engine, conn, meta = None, dbref, dbmeta
        meta.bind = conn

    #
    # actual work
    #

    local_authors = meta.tables['local_authors']

    updated = False

    with conn.begin() as transaction:

        LOGINFO("Inserting local authors...")

        ins = insert(local_authors)

        try:

            # default info
            info = {'affiliation':affiliation,
                    'server_user_id':None,
                    'server_user_role':None}

            res = conn.execute(
                ins,
                name=name,
                email=email,
                info=info
            )
            res = conn.execute(ins)
            updated = res.rowcount == 1

        except exc.IntegrityError:

            transaction.rollback()

            if not overwrite:

                LOGERROR(
                    "Author: %s with email: %s already exists "
                    "in the DB and overwrite=False. Skipping..."
                    % (name, email)
                )

            else:

                upd = update(local_authors).where(
                    local_authors.c.name == name
                ).values(
                    name=name,
                    email=email,
                    info=info
                )

                res = conn.execute(upd)
                updated = res.rowcount == 1

                LOGWARNING("Updated existing author info for author: %s" % name)
    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return updated


##############################
## NORMALIZING AUTHOR LISTS ##
##############################

def get_local_authors(dbinfo,
                      include_affiliations=False,
                      dbkwargs=None):
    '''
    This fetches and normalizes the local author list from the DB.

    '''

    #
    # get the database
    #
    dbref, dbmeta = dbinfo
    if not dbkwargs:
        dbkwargs = {}
    if isinstance(dbref, str):
        engine, conn, meta = database.get_astrocoffee_db(dbref,
                                                         dbmeta,
                                                         **dbkwargs)
    else:
        engine, conn, meta = None, dbref, dbmeta
        meta.bind = conn

    #
    # actual work
    #

    author_dict = {}

    local_authors = meta.tables['local_authors']

    with conn.begin():

        sel = select([
            local_authors.c.id,
            local_authors.c.name,
            local_authors.c.email,
            local_authors.c.info
        ]).select_from(local_authors)

        res = conn.execute(sel)
        rows = res.fetchall()
        res.close()

        if not rows or len(rows) == 0:
            LOGERROR("No local authors found.")

        else:

            #
            # normalize the full names and generate the firstinitial-lastnames
            #

            # sort the names by last-name
            actual_names = (x['name'] for x in rows)
            last_names = {x:x.split()[-1] for x in actual_names}

            sorted_rows = sorted(
                rows,
                key=lambda x:last_names[x['name']]
            )

            actual_names = [x['name'] for x in sorted_rows]
            author_emails = [x['email'] for x in sorted_rows]
            author_info = [x['info'] for x in sorted_rows]

            full_names = [x.casefold() for x in actual_names]
            full_names = [x.replace('.', ' ') for x in full_names]
            full_names = [squeeze(x) for x in full_names]

            firstinitial_lastnames = [x.split() for x in full_names]
            firstinitial_lastnames = [''.join([x[0][0],x[-1]]) for x in
                                      firstinitial_lastnames]

            full_names = [x.replace(' ','') for x in full_names]

            for fn, an, fl, em, info in zip(
                    full_names,
                    actual_names,
                    firstinitial_lastnames,
                    author_emails,
                    author_info
            ):

                this_actual_name = an
                if (include_affiliations and
                    info.get('affiliation') is not None and
                    info.get('affiliation') != ''):
                    this_actual_name = '%s (%s)' % (an, info.get('affiliation'))

                author_dict[fn] = {
                    'actual_name':this_actual_name,
                    'firstinitial_lastname':fl,
                    'email':em,
                    'info':info
                }

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return author_dict


def get_article_authors(dbinfo,
                        utcdate=None,
                        dbkwargs=None):
    '''This fetches and normalizes the article author lists from the DB on
    specified utcdate.

    '''

    #
    # get the database
    #
    dbref, dbmeta = dbinfo
    if not dbkwargs:
        dbkwargs = {}
    if isinstance(dbref, str):
        engine, conn, meta = database.get_astrocoffee_db(dbref,
                                                         dbmeta,
                                                         **dbkwargs)
    else:
        engine, conn, meta = None, dbref, dbmeta
        meta.bind = conn

    #
    # actual work
    #

    author_dict = {
        'utcdate':None,
        'articles':{}
    }

    arxiv_listings = meta.tables['arxiv_listings']

    with conn.begin():

        #
        # get the latest UTC date if not provided
        #
        if not utcdate:

            sel = select([arxiv_listings.c.utcdate]).select_from(
                arxiv_listings
            ).order_by(arxiv_listings.c.utcdate.desc())

            res = conn.execute(sel)
            utcdate = res.scalar()

        elif isinstance(utcdate, str):
            utcdate = parser.parse(utcdate).date()

        author_dict['utcdate'] = utcdate

        LOGINFO("Fetching author lists for date: %s" % utcdate)

        sel = select([
            arxiv_listings.c.id,
            arxiv_listings.c.arxiv_id,
            arxiv_listings.c.authors,
            arxiv_listings.c.title,
        ]).select_from(arxiv_listings).where(
            arxiv_listings.c.utcdate == utcdate
        )

        res = conn.execute(sel)
        rows = res.fetchall()
        res.close()

        if not rows or len(rows) == 0:
            LOGERROR("No papers found for UTC date: %s." % utcdate)

        else:

            for article in rows:

                author_dict['articles'][article['arxiv_id']] = {
                    'id':article['id'],
                    'title':article['title'],
                }

                #
                # normalize the full names and generate the
                # firstinitial-lastnames
                #

                article_authors = article['authors']['list']
                article_author_fullnames = [
                    x.casefold() for x in article_authors
                ]
                article_author_fullnames = [
                    x.replace('.', ' ') for x in article_author_fullnames
                ]
                article_author_fullnames = [
                    squeeze(x) for x in article_author_fullnames
                ]

                article_author_firstinitial_lastnames = [
                    x.split() for x in article_author_fullnames
                ]
                article_author_firstinitial_lastnames = [
                    ''.join([x[0][0],x[-1]]) for x in
                    article_author_firstinitial_lastnames
                ]

                article_author_fullnames = [
                    x.replace(' ','') for x in article_author_fullnames
                ]

                author_dict['articles'][article['arxiv_id']]['full_names'] = (
                    article_author_fullnames
                )
                author_dict['articles'][
                    article['arxiv_id']
                ]['firstinitial_lastnames'] = (
                    article_author_firstinitial_lastnames
                )
                author_dict['articles'][
                    article['arxiv_id']
                ]['actual_names'] = article_authors

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return author_dict


########################################
## AUTOMATIC TAGGING OF LOCAL AUTHORS ##
########################################

def autotag_local_authors(
        dbinfo,
        utcdate=None,
        firstname_match_threshold=93,
        fullname_match_threshold=72,
        update_db=False,
        dbkwargs=None,
):
    '''This finds all local authors on the given utcdate.

    affiliations is a dict of the form::

        affilations = {'institute.edu':'Other Institute',
                       'department.university.edu':'Other Department',...}

    '''

    #
    # get the database
    #
    dbref, dbmeta = dbinfo
    if not dbkwargs:
        dbkwargs = {}
    if isinstance(dbref, str):
        engine, conn, meta = database.get_astrocoffee_db(dbref,
                                                         dbmeta,
                                                         **dbkwargs)
    else:
        engine, conn, meta = None, dbref, dbmeta
        meta.bind = conn

    #
    # actual work
    #

    # get the local author normalized list
    local_authors = get_local_authors((conn, meta))

    local_author_fullnames = list(local_authors.keys())
    local_author_firstinitial_lastnames = [
        local_authors[x]['firstinitial_lastname']
        for x in local_author_fullnames
    ]

    # get the normalized paper authors for this UTC date
    paper_author_info = get_article_authors((conn, meta), utcdate=utcdate)

    if len(paper_author_info['articles']) == 0:
        LOGERROR("No papers found for %s" % utcdate)

    papers_with_local_authors = {}

    # now go through the lists of authors for each article and decide if they
    # are local or not

    for arxiv_id in paper_author_info['articles']:

        this_paper_info = paper_author_info['articles'][arxiv_id]
        author_full_names = this_paper_info['full_names']
        author_firstinitial_lastnames = this_paper_info[
            'firstinitial_lastnames'
        ]
        author_indices = range(len(author_full_names))

        this_paper_info['local_author_indices'] = []
        this_paper_info['local_author_specaffil'] = []

        for ind in author_indices:

            author_full_name = author_full_names[ind]
            author_firstinitial_lastname = author_firstinitial_lastnames[ind]

            full_name_match = process.extractOne(
                author_full_name,
                local_author_fullnames,
                score_cutoff=fullname_match_threshold
            )

            firstinitial_lastname_match = process.extractOne(
                author_firstinitial_lastname,
                local_author_firstinitial_lastnames,
                score_cutoff=firstname_match_threshold
            )

            if firstinitial_lastname_match and full_name_match:

                LOGWARNING(
                    "Article: %s: matched "
                    "paper author: %s to local author: %r. "
                    "First-initial-last-name score: %s, "
                    "full name score: %s" %
                    (arxiv_id,
                     author_full_name,
                     local_authors[full_name_match[0]],
                     firstinitial_lastname_match[1],
                     full_name_match[1])
                )

                # append this index to the list of local author indices
                this_paper_info['local_author_indices'].append(ind)

                # look up and append the affiliation
                local_matched_affil = (
                    local_authors[full_name_match[0]]['info']['affiliation']
                )
                if local_matched_affil is not None:
                    this_paper_info['local_author_specaffil'].append(
                        local_matched_affil
                    )

        #
        # done with all authors for this paper
        #
        if len(this_paper_info['local_author_indices']) > 0:

            # figure out if this paper should be marked as affiliated with
            # another department
            other_affil_ratio = (
                len(this_paper_info['local_author_specaffil']) /
                len(this_paper_info['local_author_indices'])
            )
            if other_affil_ratio > 0.5:
                this_paper_info['mark_other_affil'] = True
            else:
                this_paper_info['mark_other_affil'] = False

            # uniqify the special affiliations
            this_paper_info['local_author_specaffil'] = list(
                set(this_paper_info['local_author_specaffil'])
            )

            # figure out if this paper should be marked as a local paper based
            # on the author indices (i.e. the positions of the local authors in
            # the list of paper authors). if there are any authors with index <
            # 8, the locals are probably primary authors. if not, they're
            # probably part of a large collaboration and therefore unlikely to
            # talk about their papers.
            if any(x < 8 for x in this_paper_info['local_author_indices']):
                this_paper_info['mark_local'] = 'primary'
            else:
                this_paper_info['mark_local'] = 'collab'

            # append this entry to the papers_with_local_authors dict
            papers_with_local_authors[arxiv_id] = this_paper_info

    #
    # done with all papers on this date
    #

    # update the DB if requested
    updated_rows = 0

    if update_db:

        with conn.begin() as transaction:

            arxiv_listings = meta.tables['arxiv_listings']

            for arxiv_id in papers_with_local_authors:

                this_paper_info = papers_with_local_authors[arxiv_id]

                upd = update(arxiv_listings).where(
                    arxiv_listings.c.arxiv_id == arxiv_id
                ).values({
                    'local_authors':{
                        'mark_other_affil':this_paper_info['mark_other_affil'],
                        'mark_local':this_paper_info['mark_local'],
                        'indices':this_paper_info['local_author_indices'],
                        'specaffil':this_paper_info['local_author_specaffil']
                    }
                })

                try:
                    res = conn.execute(upd)
                    updated = res.rowcount
                    if updated == 0:
                        LOGERROR(
                            "Could not update paper: %s as local using: %r" %
                            (arxiv_id, this_paper_info)
                        )
                        continue
                    else:
                        updated_rows = updated_rows + updated

                except Exception:
                    transaction.rollback()
                    LOGEXCEPTION(
                        "Could not update paper: %s as local using: %r" %
                        (arxiv_id, this_paper_info)
                    )
                    continue

    papers_with_local_authors['updated_rows'] = updated_rows

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return papers_with_local_authors


##############################
## MANUAL LOCAL AUTHOR TAGS ##
##############################

def toggle_localauthor_tag(
        dbinfo,
        arxiv_id,
        local_author_indices=None,
        local_author_specaffils=None,
        dbkwargs=None,
):
    '''This toggles the local author tag for a paper.

    If local_author_indices is None, the local author tag is removed from the
    paper.

    If local_author_indices is a list of indices of the local authors in the
    paper's list of authors, the local author tag is added to the paper.

    '''

    #
    # get the database
    #
    dbref, dbmeta = dbinfo
    if not dbkwargs:
        dbkwargs = {}
    if isinstance(dbref, str):
        engine, conn, meta = database.get_astrocoffee_db(dbref,
                                                         dbmeta,
                                                         **dbkwargs)
    else:
        engine, conn, meta = None, dbref, dbmeta
        meta.bind = conn

    #
    # actual work
    #

    arxiv_listings = meta.tables['arxiv_listings']

    updated = 0

    with conn.begin() as transaction:

        if local_author_indices is None:

            update_dict = None

        else:

            if local_author_specaffils:
                specaffil = list(set(local_author_specaffils))
            else:
                specaffil = []

            update_dict = {
                'mark_other_affil':False,
                'mark_local':'primary',
                'indices':local_author_indices,
                'specaffil':specaffil
            }

        upd = update(arxiv_listings).where(
            arxiv_listings.c.arxiv_id == arxiv_id
        ).values({
            'local_authors':update_dict
        })

        try:
            res = conn.execute(upd)
            updated = res.rowcount

            if updated == 0:
                LOGERROR(
                    "Could not update paper: %s as local." % arxiv_id
                )

        except Exception:
            transaction.rollback()
            LOGEXCEPTION(
                "Could not update paper: %s as local." % arxiv_id
            )

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return updated == 1
