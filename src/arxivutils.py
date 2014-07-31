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
    'User-Agent': ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:31.0)'
                   ' Gecko/20100101 Firefox/31.0')
    }


def get_page_html(url, fakery=True):
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

        paper_abstract = squeeze(data.p.text.replace('\n',' ').strip())
        paper_title = squeeze(
            data.find_all(
                'div',class_='list-title'
            )[0].text.strip('\n').split('Title: ')[-1]
        )

        paper_authors = (
            data.find_all(
                'div',class_='list-authors'
            )[0].text.strip('\n').split('Authors: ')[-1]
            )
        paper_authors = [squeeze(x.lstrip('\n').rstrip('\n'))
                         for x in paper_authors.split(', ')]

        paper_links = link.find_all('a')[1:3]
        paper_link, arxiv_id = paper_links[0]['href'], paper_links[0].text
        paper_pdf = paper_links[1]['href']

        try:
            comment_contents = data.find('div',class_='list-comments').contents[2:]
            paper_comments = squeeze(' '.join(
                [str(x).lstrip('\n').rstrip('\n') for x in comment_contents]
                ).strip())

            # handle internal arxiv links correctly
            if '<a href="/abs"' in paper_comments:
                paper_comments = paper_comments.replace(
                    '/abs','http://www.arxiv.org/abs'
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

        cross_abstract = squeeze(data.p.text.replace('\n',' ').strip())
        cross_title = squeeze(
            data.find_all(
                'div',class_='list-title'
            )[0].text.strip('\n').lstrip('Title: ')
        )

        cross_authors = (
            data.find_all(
                'div',class_='list-authors'
            )[0].text.strip('\n').lstrip('Authors: ')
            )
        cross_authors = [squeeze(x.lstrip('\n').rstrip('\n'))
                         for x in cross_authors.split(', ')]

        cross_links = link.find_all('a')[1:3]
        cross_link, arxiv_id = cross_links[0]['href'], cross_links[0].text
        cross_pdf = cross_links[1]['href']

        try:
            comment_contents = data.find('div',class_='list-comments').contents[2:]
            cross_comments = squeeze(
                ' '.join(
                    [str(x).lstrip('\n').rstrip('\n') for x in comment_contents]
                ).strip()
            )

            # handle internal arxiv links correctly
            if '<a href="/abs"' in paper_comments:
                paper_comments = paper_comments.replace(
                    '/abs','http://www.arxiv.org/abs'
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



def arxiv_update(url='http://arxiv.org/list/astro-ph/new',
                 fakery=True,
                 pickledict=False):
    '''
    This rolls up all the functions above.

    '''

    print('updating article DB from arxiv...')

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
        pickle_fpath = 'data/%s-UT-arxiv.pickle' % now.strftime('%Y-%m-%d')
        with open(pickle_fpath,'wb') as fd:
            pickle.dump(arxiv, fd)

    return arxiv
