# -*- coding: utf-8 -*-

'''This contains functions to pull listings from the arXiv.

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

from datetime import datetime, timezone
import pickle

import requests
from bs4 import BeautifulSoup

from dateutil import parser
from tornado.escape import squeeze
from sqlalchemy import select, update, insert, exc, func, case

from . import database
from .authors import strip_affiliations

############
## CONFIG ##
############

REQUEST_HEADERS = {
    'User-Agent':(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:68.0) "
        "Gecko/20100101 Firefox/68.0"
    )
}


##############################################
## LOW-LEVEL BITS TO DOWNLOAD ARXIV LISTING ##
##############################################

def fetch_arxiv_url(url, timeout=60.0):
    '''
    This fetches new article listings from a list of arxiv URLs.

    Parameters
    ----------

    url : str
        The URL to get the arxiv listing from.

    Returns
    -------

    soupified_html : BeautifulSoup object
        This returns a BeautifulSoup object that can be used to process the
        listing. If no URL succeeded, returns None.

    '''

    html = None

    try:

        LOGINFO("Fetching new articles from URL: %s" % url)
        resp = requests.get(url, timeout=timeout, headers=REQUEST_HEADERS)
        resp.raise_for_status()

        if resp.status_code == requests.codes.ok:
            html = resp.text
        else:
            html = None

    except Exception:

        LOGEXCEPTION("Could not fetch HTML for URL: %s" % url)
        html = None

    if html is not None:

        soup = BeautifulSoup(html, 'lxml')
        return soup

    else:

        return None


def parse_arxiv_soup(soup):
    '''
    This parses the soupified arxiv listing into dicts.

    Parameters
    ----------

    soup : BeautifulSoup object
        This is a BeautifulSoup object returned from the
        :func:`.fetch_new_articles` function.

    Returns
    -------

    (new_papers, cross_lists) : tuple
        ``new_papers`` contains the new articles from the URL. ``cross_lists``
        contains the cross-listings from the URL.

    '''

    # get all HTML DL elements that make up each abstract listing
    docparts = soup.find_all('dl')

    # if the structure doesn't match what we expect: (new, crosslists,
    # replacements), then take the first bit only (since that's guaranteed to be
    # new papers)
    if len(docparts) < 3:

        papers = docparts[0]
        paperlinks, paperdata = (papers.find_all('dt'),
                                 papers.find_all('div', class_='meta'))
        crosslinks, crossdata = [], []

    # otherwise, we can parse as usual
    elif len(docparts) == 3:
        papers, crosslists, replacements = docparts

        paperlinks, paperdata = (papers.find_all('dt'),
                                 papers.find_all('div', class_='meta'))
        crosslinks, crossdata = (crosslists.find_all('dt'),
                                 crosslists.find_all('div', class_='meta'))

    #
    # now parse the new papers
    #
    new_papers = {}

    npapers = len(paperlinks)

    for ind, link, data in zip(range(npapers), paperlinks, paperdata):

        try:
            paper_abstract = squeeze(data.p.text.replace('\n',' ').strip())
        except Exception:
            paper_abstract = ''

        paper_title = squeeze(
            data.find_all(
                'div',class_='list-title'
            )[0].text.replace('\n','').replace('Title:','',1)
        )

        paper_authors = (
            data.find_all(
                'div',class_='list-authors'
            )[0].text.replace('\n','').replace('Authors:','',1)
        )
        paper_authors = strip_affiliations(paper_authors)

        paper_links = link.find_all('a')[1:3]
        paper_link, arxiv_id = paper_links[0]['href'], paper_links[0].text
        paper_pdf = paper_links[1]['href']

        try:
            comment_contents = data.find(
                'div',class_='list-comments'
            ).contents[2:]
            paper_comments = squeeze(
                ' '.join(
                    [str(x).replace('\n','') for x in comment_contents]
                ).strip()
            )

            # handle internal arxiv links correctly
            if '<a href="/abs' in paper_comments:
                paper_comments = paper_comments.replace(
                    '/abs','https://arxiv.org/abs'
                )

        except AttributeError:
            paper_comments = ''

        new_papers[ind+1] = {
            'authors':paper_authors,
            'title':paper_title,
            'abstract':paper_abstract,
            'comments':paper_comments,
            'arxiv':arxiv_id,
            'link':paper_link,
            'pdf':paper_pdf
        }

    #
    # parse the cross-lists
    #
    cross_lists = {}

    ncross = len(crosslinks)

    for ind, link, data in zip(range(ncross), crosslinks, crossdata):

        try:
            cross_abstract = squeeze(data.p.text.replace('\n',' ').strip())
        except Exception:
            cross_abstract = ''

        cross_title = squeeze(
            data.find_all(
                'div',class_='list-title'
            )[0].text.replace('\n','').replace('Title:','',1)
        )

        cross_authors = (
            data.find_all(
                'div',class_='list-authors'
            )[0].text.replace('\n','').replace('Authors:','',1)
        )
        cross_authors = strip_affiliations(cross_authors)

        cross_links = link.find_all('a')[1:3]
        cross_link, arxiv_id = cross_links[0]['href'], cross_links[0].text
        cross_pdf = cross_links[1]['href']

        # figure out which original arxiv this came from
        try:
            cltext = link.text
            cltext_xlind_start = cltext.index('cross-list')
            cltext_xlind_end = cltext.index('[pdf') - 2

            # annotate the title with the original arxiv category
            cltext = cltext[cltext_xlind_start:cltext_xlind_end]
            cross_title = u'[%s] %s' % (cltext, cross_title)

        # if the cross-list doesn't say where it came from, just add a
        # [cross-list] annotation
        except Exception:
            cross_title = u'[cross-list] %s' % cross_title

        try:
            comment_contents = data.find(
                'div',class_='list-comments'
            ).contents[2:]
            cross_comments = squeeze(
                ' '.join(
                    [str(x).replace('\n','') for x in comment_contents]
                ).strip()
            )

            # handle internal arxiv links correctly
            if '<a href="/abs' in paper_comments:
                paper_comments = paper_comments.replace(
                    '/abs','https://arxiv.org/abs'
                )

        except AttributeError:
            cross_comments = ''

        cross_lists[ind+1] = {
            'authors':cross_authors,
            'title':cross_title,
            'abstract':cross_abstract,
            'comments':cross_comments,
            'arxiv':arxiv_id,
            'link':cross_link,
            'pdf':cross_pdf
        }

    return new_papers, cross_lists


#############################
## FETCHING ARXIV LISTINGS ##
#############################

def fetch_arxiv_listing(
        urls=("https://arxiv.org/list/astro-ph/new",
              "https://arxiv.org/list/astro-ph/pastweek?show=350"),
        timeout=60.0,
        savepickle=None,
):
    '''This gets a new arxiv listing.

    Parameters
    ----------

    urls : list of str
        The list of URLs to try, one after the other, to get a new arxiv
        listing. The first URL that is retrieved successfully wins.

    timeout : int
        The timeout in seconds to use when fetching the listings.

    savepickle : str or None
        If not None, is the filename to where the parsed arxiv listing dict will
        be saved.

    Returns
    -------

    arxiv : dict
        A dict containing new articles and cross-lists suitable for further
        processing and insertion into a database.

    '''

    arxiv_dict = None
    now = datetime.now(tz=timezone.utc)

    for url in urls:

        try:

            soup = fetch_arxiv_url(url, timeout=timeout)
            if not soup:
                LOGERROR("Could not get articles from %s" % url)
                continue

            new_papers, cross_lists = parse_arxiv_soup(soup)

            if len(new_papers) == 0:
                LOGERROR("No new papers available from URL: %s" % url)
                continue

            arxiv_dict = {
                'utc':now,
                'npapers':len(new_papers),
                'new_papers':new_papers,
                'ncrosslists':len(cross_lists),
                'cross_lists':cross_lists,
            }

            # if everything finished OK for this URL, break out
            break

        except Exception:
            LOGEXCEPTION("Could not get articles from %s" % url)
            continue

    if not arxiv_dict:

        LOGERROR("Could not get arxiv listings for UTC datetime: %s. "
                 "URLs tried: %r" % (now, urls))
        return None

    # if everything succeeded OK, save the pickle if requested and return the
    # dict
    if savepickle is not None:

        with open(savepickle, 'wb') as outfd:
            pickle.dump(arxiv_dict, outfd, pickle.HIGHEST_PROTOCOL)

    return arxiv_dict


#######################################
## INSERTING AND RETRIEVING LISTINGS ##
#######################################

def insert_arxiv_listing(dbinfo,
                         arxiv_dict,
                         dbkwargs=None,
                         overwrite=False):
    '''
    This inserts an arxiv listing into the DB.

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
    with conn.begin() as transaction:

        utcdate = arxiv_dict['utc'].date()
        arxiv_listings = meta.tables['arxiv_listings']
        ins = insert(arxiv_listings)

        LOGINFO(
            "Inserting new arXiv articles for UTC date: %s" % utcdate
        )

        for new_paper in arxiv_dict['new_papers']:

            title = arxiv_dict['new_papers'][new_paper]['title']
            arxiv_id = arxiv_dict['new_papers'][new_paper]['arxiv']
            authors_json = {
                'list': arxiv_dict['new_papers'][new_paper]['authors']
            }
            comments = arxiv_dict['new_papers'][new_paper]['comments']
            abstract = arxiv_dict['new_papers'][new_paper]['abstract']
            link = (
                'https://arxiv.org%s' %
                arxiv_dict['new_papers'][new_paper]['link']
            )
            pdf = (
                'https://arxiv.org%s' %
                arxiv_dict['new_papers'][new_paper]['pdf']
            )

            try:
                conn.execute(
                    ins,
                    {'utcdate':utcdate,
                     'day_serial':new_paper,
                     'title':title,
                     'article_type':'newarticle',
                     'arxiv_id':arxiv_id,
                     'authors':authors_json,
                     'comments':comments,
                     'abstract':abstract,
                     'link':link,
                     'pdf':pdf}
                )
            except exc.IntegrityError:

                transaction.rollback()

                if not overwrite:
                    LOGERROR("Article with ID: %s already exists! "
                             "Skipping..." % arxiv_id)
                    continue

                upd = update(arxiv_listings).where(
                    arxiv_listings.c.arxiv_id == arxiv_id
                ).values(
                    {'utcdate':utcdate,
                     'day_serial':new_paper,
                     'title':title,
                     'article_type':'newarticle',
                     'arxiv_id':arxiv_id,
                     'authors':authors_json,
                     'comments':comments,
                     'abstract':abstract,
                     'link':link,
                     'pdf':pdf}
                )
                conn.execute(upd)
                LOGWARNING("Updated existing listing for article: %s" %
                           arxiv_id)

        LOGINFO(
            "Inserting cross-listed arXiv articles for UTC date: %s" % utcdate
        )

        for cross_list in arxiv_dict['cross_lists']:

            title = arxiv_dict['cross_lists'][cross_list]['title']
            arxiv_id = arxiv_dict['cross_lists'][cross_list]['arxiv']
            authors_json = {
                'list': arxiv_dict['cross_lists'][cross_list]['authors']
            }
            comments = arxiv_dict['cross_lists'][cross_list]['comments']
            abstract = arxiv_dict['cross_lists'][cross_list]['abstract']
            link = (
                'https://arxiv.org%s' %
                arxiv_dict['cross_lists'][cross_list]['link']
            )
            pdf = (
                'https://arxiv.org%s' %
                arxiv_dict['cross_lists'][cross_list]['pdf']
            )

            try:
                conn.execute(
                    ins,
                    {'utcdate':utcdate,
                     'day_serial':cross_list,
                     'title':title,
                     'article_type':'crosslist',
                     'arxiv_id':arxiv_id,
                     'authors':authors_json,
                     'comments':comments,
                     'abstract':abstract,
                     'link':link,
                     'pdf':pdf}
                )
            except exc.IntegrityError:

                transaction.rollback()

                if not overwrite:
                    LOGERROR("Article with ID: %s already exists! "
                             "Skipping..." % arxiv_id)
                    continue

                upd = update(arxiv_listings).where(
                    arxiv_listings.c.arxiv_id == arxiv_id
                ).values(
                    {'utcdate':utcdate,
                     'day_serial':cross_list,
                     'title':title,
                     'article_type':'crosslist',
                     'arxiv_id':arxiv_id,
                     'authors':authors_json,
                     'comments':comments,
                     'abstract':abstract,
                     'link':link,
                     'pdf':pdf}
                )
                conn.execute(upd)
                LOGWARNING("Updated existing listing for article: %s" %
                           arxiv_id)
    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()


def get_single_article(dbinfo,
                       arxiv_id,
                       dbkwargs=None):
    '''
    This gets a single article's listing.

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

    row = None

    with conn.begin():

        arxiv_listings = meta.tables['arxiv_listings']

        sel = select([
            arxiv_listings.c.day_serial,
            arxiv_listings.c.arxiv_id,
            arxiv_listings.c.title,
            arxiv_listings.c.authors,
            arxiv_listings.c.comments,
            arxiv_listings.c.abstract,
            arxiv_listings.c.link,
            arxiv_listings.c.pdf,
            arxiv_listings.c.local_authors,
            arxiv_listings.c.nvotes,
            arxiv_listings.c.voter_info,
            arxiv_listings.c.presenter_info,
            arxiv_listings.c.reserved,
            arxiv_listings.c.reserver_info,
            arxiv_listings.c.reserved_on,
            arxiv_listings.c.reserved_until,
        ]).select_from(
            arxiv_listings
        ).where(
            arxiv_listings.c.arxiv_id == arxiv_id
        )

        res = conn.execute(sel)
        row = res.first()

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return row


def get_arxiv_listing(dbinfo,
                      utcdate=None,
                      dbkwargs=None):
    '''
    This gets all articles from the database for the given UTC date.

    Returns a dict of the form::

        retdict = {
            'utcdate':utcdate,
            'local_papers':[],
            'papers_with_votes':[],
            'papers_with_presenters':[],
            'reserved_papers':[],
            'other_new_papers':[],
            'cross_listed_papers':[]
        }

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

    retdict = {
        'utcdate':utcdate,
        'local_papers':[],
        'papers_with_votes':[],
        'papers_with_presenters':[],
        'reserved_papers':[],
        'other_new_papers':[],
        'cross_listed_papers':[]
    }

    #
    # actual work
    #
    with conn.begin() as transaction:

        arxiv_listings = meta.tables['arxiv_listings']

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

        LOGINFO("Fetching arxiv listings for date: %s" % utcdate)
        retdict['utcdate'] = utcdate

        #
        # first, fetch only the local papers
        #
        sel = select([
            arxiv_listings.c.day_serial,
            arxiv_listings.c.arxiv_id,
            arxiv_listings.c.title,
            arxiv_listings.c.authors,
            arxiv_listings.c.comments,
            arxiv_listings.c.abstract,
            arxiv_listings.c.link,
            arxiv_listings.c.pdf,
            arxiv_listings.c.local_authors,
            arxiv_listings.c.nvotes,
            arxiv_listings.c.voter_info,
            arxiv_listings.c.presenter_info,
            arxiv_listings.c.reserved,
            arxiv_listings.c.reserver_info,
            arxiv_listings.c.reserved_on,
            arxiv_listings.c.reserved_until,
        ]).select_from(
            arxiv_listings
        ).where(
            arxiv_listings.c.utcdate == utcdate
        ).where(
            arxiv_listings.c.local_authors.isnot(None)
        ).where(
            arxiv_listings.c.reserved.is_(False)
        ).where(
            arxiv_listings.c.presenter_info.is_(None)
        ).order_by(
            arxiv_listings.c.nvotes.desc()
        )

        try:

            res = conn.execute(sel)
            local_papers_rows = res.fetchall()
            res.close()

        except Exception:
            LOGEXCEPTION("Could not fetch local papers for date: %s" % utcdate)

            transaction.rollback()
            local_papers_rows = []

        retdict['local_papers'] = local_papers_rows

        #
        # next, fetch the papers with presenters (from either new papers
        # or cross-lists)
        #
        sel = select([
            arxiv_listings.c.day_serial,
            arxiv_listings.c.arxiv_id,
            arxiv_listings.c.title,
            arxiv_listings.c.authors,
            arxiv_listings.c.comments,
            arxiv_listings.c.abstract,
            arxiv_listings.c.link,
            arxiv_listings.c.pdf,
            arxiv_listings.c.local_authors,
            arxiv_listings.c.nvotes,
            arxiv_listings.c.voter_info,
            arxiv_listings.c.presenter_info,
            arxiv_listings.c.reserved,
            arxiv_listings.c.reserver_info,
            arxiv_listings.c.reserved_on,
            arxiv_listings.c.reserved_until,
        ]).select_from(
            arxiv_listings
        ).where(
            arxiv_listings.c.utcdate == utcdate
        ).where(
            arxiv_listings.c.presenter_info.isnot(None)
        ).where(
            arxiv_listings.c.local_authors.is_(None)
        ).where(
            arxiv_listings.c.reserved.is_(False)
        ).order_by(
            arxiv_listings.c.nvotes.desc()
        )

        try:

            res = conn.execute(sel)
            papers_with_presenters_rows = res.fetchall()
            res.close()

        except Exception:
            LOGEXCEPTION(
                "Could not fetch papers with presenters for date: %s" % utcdate
            )

            transaction.rollback()
            papers_with_presenters_rows = []

        retdict['papers_with_presenters'] = papers_with_presenters_rows

        #
        # next, fetch the papers with voters only (from either new papers or
        # cross-lists)
        #
        sel = select([
            arxiv_listings.c.day_serial,
            arxiv_listings.c.arxiv_id,
            arxiv_listings.c.title,
            arxiv_listings.c.authors,
            arxiv_listings.c.comments,
            arxiv_listings.c.abstract,
            arxiv_listings.c.link,
            arxiv_listings.c.pdf,
            arxiv_listings.c.local_authors,
            arxiv_listings.c.nvotes,
            arxiv_listings.c.voter_info,
            arxiv_listings.c.presenter_info,
            arxiv_listings.c.reserved,
            arxiv_listings.c.reserver_info,
            arxiv_listings.c.reserved_on,
            arxiv_listings.c.reserved_until,
        ]).select_from(
            arxiv_listings
        ).where(
            arxiv_listings.c.utcdate == utcdate
        ).where(
            arxiv_listings.c.nvotes > 0
        ).where(
            arxiv_listings.c.presenter_info.is_(None)
        ).where(
            arxiv_listings.c.local_authors.is_(None)
        ).where(
            arxiv_listings.c.reserved.is_(False)
        ).order_by(
            arxiv_listings.c.nvotes.desc()
        )

        try:

            res = conn.execute(sel)
            papers_with_votes_rows = res.fetchall()
            res.close()

        except Exception:
            LOGEXCEPTION(
                "Could not fetch papers with votes for date: %s" % utcdate
            )

            transaction.rollback()
            papers_with_votes_rows = []

        retdict['papers_with_votes'] = papers_with_votes_rows

        #
        # next, fetch the papers that were reserved only (from either new papers
        # or cross-lists)
        #

        # show only those reserved papers that are still within the requested
        # time-range
        sel = select([
            arxiv_listings.c.day_serial,
            arxiv_listings.c.arxiv_id,
            arxiv_listings.c.title,
            arxiv_listings.c.authors,
            arxiv_listings.c.comments,
            arxiv_listings.c.abstract,
            arxiv_listings.c.link,
            arxiv_listings.c.pdf,
            arxiv_listings.c.local_authors,
            arxiv_listings.c.nvotes,
            arxiv_listings.c.voter_info,
            arxiv_listings.c.presenter_info,
            arxiv_listings.c.reserved,
            arxiv_listings.c.reserver_info,
            arxiv_listings.c.reserved_on,
            arxiv_listings.c.reserved_until,
        ]).select_from(
            arxiv_listings
        ).where(
            arxiv_listings.c.utcdate == utcdate
        ).where(
            arxiv_listings.c.reserved.is_(True)
        ).where(
            arxiv_listings.c.reserved_until > datetime.utcnow().date()
        ).order_by(
            arxiv_listings.c.nvotes.desc()
        )

        try:

            res = conn.execute(sel)
            reserved_papers_rows = res.fetchall()
            res.close()

        except Exception:
            LOGEXCEPTION(
                "Could not fetch reserved papers for date: %s" % utcdate
            )

            transaction.rollback()
            reserved_papers_rows = []

        retdict['reserved_papers'] = reserved_papers_rows

        #
        # next, fetch the new papers only (not cross-lists)
        #
        sel = select([
            arxiv_listings.c.day_serial,
            arxiv_listings.c.arxiv_id,
            arxiv_listings.c.title,
            arxiv_listings.c.authors,
            arxiv_listings.c.comments,
            arxiv_listings.c.abstract,
            arxiv_listings.c.link,
            arxiv_listings.c.pdf,
            arxiv_listings.c.local_authors,
            arxiv_listings.c.nvotes,
            arxiv_listings.c.voter_info,
            arxiv_listings.c.presenter_info,
            arxiv_listings.c.reserved,
            arxiv_listings.c.reserver_info,
            arxiv_listings.c.reserved_on,
            arxiv_listings.c.reserved_until,
        ]).select_from(
            arxiv_listings
        ).where(
            arxiv_listings.c.utcdate == utcdate
        ).where(
            arxiv_listings.c.nvotes == 0
        ).where(
            arxiv_listings.c.article_type == 'newarticle'
        ).where(
            arxiv_listings.c.reserved.is_(False)
        ).where(
            arxiv_listings.c.presenter_info.is_(None)
        ).where(
            arxiv_listings.c.local_authors.is_(None)
        ).order_by(
            arxiv_listings.c.day_serial.asc()
        )

        try:

            res = conn.execute(sel)
            other_new_papers_rows = res.fetchall()
            res.close()

        except Exception:
            LOGEXCEPTION(
                "Could not fetch reserved papers for date: %s" % utcdate
            )

            transaction.rollback()
            other_new_papers_rows = []

        retdict['other_new_papers'] = other_new_papers_rows

        #
        # finally, fetch the cross-lists
        #
        sel = select([
            arxiv_listings.c.day_serial,
            arxiv_listings.c.arxiv_id,
            arxiv_listings.c.title,
            arxiv_listings.c.authors,
            arxiv_listings.c.comments,
            arxiv_listings.c.abstract,
            arxiv_listings.c.link,
            arxiv_listings.c.pdf,
            arxiv_listings.c.local_authors,
            arxiv_listings.c.nvotes,
            arxiv_listings.c.voter_info,
            arxiv_listings.c.presenter_info,
            arxiv_listings.c.reserved,
            arxiv_listings.c.reserver_info,
            arxiv_listings.c.reserved_on,
            arxiv_listings.c.reserved_until,
        ]).select_from(
            arxiv_listings
        ).where(
            arxiv_listings.c.utcdate == utcdate
        ).where(
            arxiv_listings.c.nvotes == 0
        ).where(
            arxiv_listings.c.article_type == 'crosslist'
        ).where(
            arxiv_listings.c.reserved.is_(False)
        ).where(
            arxiv_listings.c.presenter_info.is_(None)
        ).where(
            arxiv_listings.c.local_authors.is_(None)
        ).order_by(
            arxiv_listings.c.day_serial.asc()
        )

        try:

            res = conn.execute(sel)
            cross_listed_papers_rows = res.fetchall()
            res.close()

        except Exception:
            LOGEXCEPTION(
                "Could not fetch reserved papers for date: %s" % utcdate
            )

            transaction.rollback()
            cross_listed_papers_rows = []

        retdict['cross_listed_papers'] = cross_listed_papers_rows

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    return retdict


###################
## PAPER ARCHIVE ##
###################

MONTH_NAMES = {x:datetime(year=2019,month=x,day=12) for x in range(1,13)}


def group_arxiv_dates(dates, npapers, nlocal, nvoted):
    '''
    This takes a list of datetime.dates and the number of papers corresponding
    to each date and builds a nice dict out of it, allowing the following
    listing (in rev-chron order) to be made:

    YEAR X

    Month X:

    Date X --- <strong>YY<strong> papers

    .
    .
    .

    YEAR 1

    Month 1:

    Date 1 --- <strong>YY<strong> papers

    '''

    years, months = [], []

    for x in dates:
        years.append(x.year)
        months.append(x.month)

    unique_years = set(years)
    unique_months = set(months)

    yeardict = {}

    for year in unique_years:
        yeardict[year] = {}
        for month in unique_months:
            yeardict[year][MONTH_NAMES[month]] = [
                (x,y,z,w) for (x,y,z,w) in zip(dates, npapers, nlocal, nvoted)
                if (x.year == year and x.month == month)
            ]
        for month in yeardict[year].copy():
            if not yeardict[year][month]:
                del yeardict[year][month]

    return yeardict


def get_coffee_archive(
        dbinfo,
        start_date=None,
        end_date=None,
        dbkwargs=None,
        returndict=False,
):
    '''
    This returns all the article counts by date.

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

    if isinstance(start_date, str):
        start_date = parser.parse(start_date).date()

    if isinstance(end_date, str):
        end_date = parser.parse(end_date).date()

    with conn.begin() as transaction:

        arxiv_listings = meta.tables['arxiv_listings']

        sel = select([
            arxiv_listings.c.utcdate,
            func.count().label('total_count'),
            func.sum(
                case([
                    (arxiv_listings.c.local_authors.isnot(None), 1),
                    (arxiv_listings.c.local_authors.is_(None), 0)
                ])
            ).label('localauthor_count'),
            func.sum(
                case([
                    (arxiv_listings.c.nvotes > 0, 1),
                    (arxiv_listings.c.nvotes == 0, 0)
                ])
            ).label('voted_count')
        ]).select_from(
            arxiv_listings
        ).group_by(
            arxiv_listings.c.utcdate
        ).order_by(
            arxiv_listings.c.utcdate.desc()
        )

        if start_date is not None:
            sel = sel.where(
                arxiv_listings.c.utcdate >= start_date
            )

        if end_date is not None:
            sel = sel.where(
                arxiv_listings.c.utcdate <= end_date
            )

        try:

            res = conn.execute(sel)
            rows = res.fetchall()
            res.close()

        except Exception:
            LOGEXCEPTION("Could not fetch coffee archive.")
            transaction.rollback()
            rows = []

    #
    # at the end, shut down the DB
    #
    if engine:
        conn.close()
        meta.bind = None
        engine.dispose()

    if len(rows) == 0:
        LOGERROR("No article lists found for the requested dates.")

    if returndict:

        if len(rows) > 0:

            retdict = group_arxiv_dates(
                [x['utcdate'] for x in rows],
                [x['total_count'] for x in rows],
                [x['localauthor_count'] for x in rows],
                [x['voted_count'] for x in rows],
            )
            return retdict
        else:
            return None

    else:

        return rows
