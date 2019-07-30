# -*- coding: utf-8 -*-

'''This contains functions to pull listings from the arXiv.

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

from hashlib import sha256
from datetime import datetime, timezone
import pickle

import requests
from bs4 import BeautifulSoup

from tornado.escape import squeeze
from sqlalchemy import select, update, func, distinct, insert, exc

from . import database


############
## CONFIG ##
############

REQUEST_HEADERS = {
    'User-Agent':(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:68.0) "
        "Gecko/20100101 Firefox/68.0"
    )
}


####################
## LOW-LEVEL BITS ##
####################

def fetch_new_articles(url, timeout=60.0):
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

    (new_papers, cross_lists, listing_hash) : tuple
        ``new_papers`` contains the new articles from the URL. ``cross_lists``
        contains the cross-listings from the URL. ``listing_hash`` is a SHA256
        hash of the first five articles in the ``new_papers`` dict to help
        indicate if the article listing has been updated when compared to a
        previous listing.

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
        paper_authors = [squeeze(x.replace('\n',''))
                         for x in paper_authors.split(', ')]

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
        cross_authors = [squeeze(x.replace('\n',''))
                         for x in cross_authors.split(', ')]

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

    # hash the first five new paper arxiv IDs so we can tell if the listings
    # have been updated
    listing_hash = sha256(
        (' '.join([new_papers[x]['arxiv'] for x in range(1,5)])).encode()
    ).hexdigest()

    return new_papers, cross_lists, listing_hash


def get_arxiv_listing(
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

            soup = fetch_new_articles(url, timeout=timeout)
            if not soup:
                LOGERROR("Could not get articles from %s" % url)
                continue

            new_papers, cross_lists, listing_hash = parse_arxiv_soup(soup)

            if len(new_papers) == 0:
                LOGERROR("No new papers available from URL: %s" % url)
                continue

            arxiv_dict = {
                'utc':now,
                'npapers':len(new_papers),
                'new_papers':new_papers,
                'ncrosslists':len(cross_lists),
                'cross_lists':cross_lists,
                'hash':listing_hash
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
            "Inserting arXiv articles for UTC date: %s" % utcdate
        )

        for new_paper in arxiv_dict['new_papers']:

            title = arxiv_dict['new_papers'][new_paper]['title']
            arxiv_id = arxiv_dict['new_papers'][new_paper]['arxiv']
            authors_string = '|'.join(
                arxiv_dict['new_papers'][new_paper]['authors']
            )
            comments = arxiv_dict['new_papers'][new_paper]['comments']
            abstract = arxiv_dict['new_papers'][new_paper]['abstract']
            link = (
                'https://arxiv.org/%s' %
                arxiv_dict['new_papers'][new_paper]['link']
            )
            pdf = (
                'https://arxiv.org/%s' %
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
                     'authors':authors_string,
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
                     'authors':authors_string,
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
