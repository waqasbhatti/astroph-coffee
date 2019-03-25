#!/usr/bin/env python

'''arxivutils.py - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jun 2014

Contains useful functions for getting and parsing arxiv listings for the
astroph-coffee server.

'''

import random
import time
from datetime import date, datetime

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from tornado.escape import squeeze
import requests, requests.exceptions

from pytz import utc

CHUNKSIZE = 64
REQUEST_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0)'
                   ' Gecko/20100101 Firefox/40.0')
    }


def get_page_html(url, fakery=False):
    '''
    This connects to the arxiv server and downloads the HTML of the page, while
    faking some activity if requested via the Selenium browser driver.

    '''

    if fakery:

        driver = webdriver.Firefox()
        driver.get(url)
        html = driver.page_source

        time.sleep(5.0)

        npagedowns = 2 + int(random.random()*20.0)
        for x in range(npagedowns):
            elem = driver.find_element_by_tag_name('body')
            elem.send_keys(Keys.PAGE_DOWN)
            time.sleep(10.0 + random.random()*10.0)

        # then quit
        driver.quit()

    else:

        pagerequest = requests.get(url,
                                   headers=REQUEST_HEADERS)

        if pagerequest.status_code == requests.codes.ok:
            html = pagerequest.text
        else:
            html = None

    return html


def soupify(htmldoc):
    '''
    Loads the HTML document obtained by get_page_html into an instance of
    BeautifulSoup.

    '''

    return BeautifulSoup(htmldoc)


def get_arxiv_lists(soup):
    '''
    This gets a list of articles from the soupified HTML document.

    '''

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


    return paperlinks, paperdata, crosslinks, crossdata



def get_arxiv_articles(paperlinks, paperdata, crosslinks, crossdata):

    paperdict = {}
    crossdict = {}

    for ind, link, data in zip(range(len(paperlinks)), paperlinks, paperdata):

        try:
            paper_abstract = squeeze(data.p.text.replace('\n',' ').strip())
        except:
            paper_abstract = ''

        paper_title = squeeze(
            data.find_all(
                'div',class_='list-title'
            )[0].text.strip('\n').replace('Title:','',1)
        )

        paper_authors = (
            data.find_all(
                'div',class_='list-authors'
            )[0].text.strip('\n').replace('Authors:','',1)
            )
        paper_authors = [squeeze(x.lstrip('\n').rstrip('\n'))
                         for x in paper_authors.split(', ')]

        paper_links = link.find_all('a')[1:3]
        paper_link, arxiv_id = paper_links[0]['href'], paper_links[0].text
        paper_pdf = paper_links[1]['href']

        try:
            comment_contents = data.find(
                'div',class_='list-comments'
            ).contents[2:]
            paper_comments = squeeze(' '.join(
                [str(x).lstrip('\n').rstrip('\n') for x in comment_contents]
                ).strip())

            # handle internal arxiv links correctly
            if '<a href="/abs' in paper_comments:
                paper_comments = paper_comments.replace(
                    '/abs','https://arxiv.org/abs'
                    )

        except AttributeError:
            paper_comments = ''


        paperdict[ind+1] = {'authors':paper_authors,
                            'title':paper_title,
                            'abstract':paper_abstract,
                            'comments':paper_comments,
                            'arxiv':arxiv_id,
                            'link':paper_link,
                            'pdf':paper_pdf}


    for ind, link, data in zip(range(len(crosslinks)), crosslinks, crossdata):

        try:
            cross_abstract = squeeze(data.p.text.replace('\n',' ').strip())
        except:
            cross_abstract = ''

        cross_title = squeeze(
            data.find_all(
                'div',class_='list-title'
            )[0].text.strip('\n').replace('Title:','',1)
        )

        cross_authors = (
            data.find_all(
                'div',class_='list-authors'
            )[0].text.strip('\n').replace('Authors:','',1)
            )
        cross_authors = [squeeze(x.lstrip('\n').rstrip('\n'))
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
        except:
            cross_title = u'[cross-list] %s' % cross_title

        try:
            comment_contents = data.find(
                'div',class_='list-comments'
            ).contents[2:]
            cross_comments = squeeze(
                ' '.join(
                    [str(x).lstrip('\n').rstrip('\n') for x in comment_contents]
                ).strip()
            )

            # handle internal arxiv links correctly
            if '<a href="/abs' in paper_comments:
                paper_comments = paper_comments.replace(
                    '/abs','https://arxiv.org/abs'
                    )

        except AttributeError:
            cross_comments = ''

        crossdict[ind+1] = {'authors':cross_authors,
                            'title':cross_title,
                            'abstract':cross_abstract,
                            'comments':cross_comments,
                            'arxiv':arxiv_id,
                            'link':cross_link,
                            'pdf':cross_pdf}


    return paperdict, crossdict



def arxiv_update(url='https://arxiv.org/list/astro-ph/new',
                 alturl='https://arxiv.org/list/astro-ph/pastweek?show=350',
                 fakery=False,
                 pickledict=False):
    '''
    This rolls up all the functions above.

    '''

    arxiv = None

    try:

        print('updating article DB from arxiv /new page: %s' % url)

        html = get_page_html(url, fakery=fakery)
        soup = soupify(html)

        paperlinks, paperdata, crosslinks, crossdata = get_arxiv_lists(soup)

        # process the papers and crosslists
        paperdict, crosslistdict = get_arxiv_articles(paperlinks, paperdata,
                                                      crosslinks, crossdata)
        now = datetime.now(tz=utc)

        arxiv = {'utc':now,
                 'npapers':len(paperdict.keys()),
                 'papers':paperdict,
                 'ncrosslists':len(crosslistdict.keys()),
                 'crosslists':crosslistdict}

        if pickledict:
            import cPickle as pickle
            pickle_fpath = 'data/%s-UT-arxiv.pkl' % now.strftime('%Y-%m-%d')
            with open(pickle_fpath,'wb') as fd:
                pickle.dump(arxiv, fd, pickle.HIGHEST_PROTOCOL)

        return arxiv

    except Exception as e:

        print('could not get /new page, trying alternative '
              '/recent page: %s' % alturl)

        resp = requests.get(alturl)
        resphtml = resp.text

        soup = BeautifulSoup(resphtml)
        docparts = soup.find_all('dl')

        # the first dl is for the most recent date

        # get the paper links
        paperlinks = docparts[0].find_all('dt')
        paperdata = docparts[0].find_all('div',class_='_meta')

        # ignore the cross links and treat them as part of the paper list
        crosslinks, crossdata = [], []

        paperdict, crosslistdict = get_arxiv_articles(
            paperlinks, paperdata, crosslinks, crossdata
        )

        # the rest of the bits are the same
        now = datetime.now(tz=utc)

        arxiv = {'utc':now,
                 'npapers':len(paperdict.keys()),
                 'papers':paperdict,
                 'ncrosslists':len(crosslistdict.keys()),
                 'crosslists':crosslistdict}

        if pickledict:
            import cPickle as pickle
            pickle_fpath = 'data/%s-UT-arxiv.pkl' % now.strftime('%Y-%m-%d')
            with open(pickle_fpath,'wb') as fd:
                pickle.dump(arxiv, fd, pickle.HIGHEST_PROTOCOL)

        return arxiv


    finally:

        if arxiv is None:
            print('could not get arxiv update '
                  'from /new URL: %s or /recent URL: %s' % (url, alturl))
