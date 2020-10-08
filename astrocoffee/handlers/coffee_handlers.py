# -*- coding: utf-8 -*-

'''This contains the main Astro-Coffee URL handlers.

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

from functools import partial

from tornado.escape import xhtml_escape

from . import basehandler
from . import coffee_workers as workers
from .. import arxivupdate


#########################
## BASIC PAGE HANDLERS ##
#########################

class IndexHandler(basehandler.BaseHandler):

    def get(self):
        '''
        This handles the basic index page.

        '''

        self.render(
            'index.html',
            baseurl=self.conf.base_url,
            current_user=self.current_user,
            conf=self.conf,
            page_title='Astro-Coffee@%s' % self.conf.institution_short_name,
            flash_message_list=self.flash_message_list,
            alert_type=self.alert_type,
        )


class LocalAuthorListHandler(basehandler.BaseHandler):

    async def get(self):
        '''
        This handles the local author list page.

        '''

        # get the list of local authors
        author_list, local_authors = await self.loop.run_in_executor(
            self.executor,
            workers.get_local_authors,
        )

        self.render(
            'local-authors.html',
            baseurl=self.conf.base_url,
            current_user=self.current_user,
            conf=self.conf,
            page_title='List of local authors',
            flash_message_list=self.flash_message_list,
            alert_type=self.alert_type,
            local_authors=local_authors,
            author_list=author_list
        )


class AboutHandler(basehandler.BaseHandler):

    def get(self):
        '''
        This handles the about page.

        '''

        self.render(
            'about-page.html',
            baseurl=self.conf.base_url,
            current_user=self.current_user,
            conf=self.conf,
            page_title='About the astro-coffee server',
            flash_message_list=self.flash_message_list,
            alert_type=self.alert_type,
        )


class ArticleListingHandler(basehandler.BaseHandler):

    async def get(self):
        '''This handles the article listings and switches between voting
        and list mode.

        Also handles the main arxiv section and the archive listings.

        '''

        # check if we're in vote mode and show the voting listing if so
        in_voting_mode = arxivupdate.voting_window_active(
            self.conf.voting_start_localtime,
            self.conf.voting_end_localtime,
            self.conf.coffee_days,
            self.conf.coffee_at_localtime,
        )

        # FIXME: for dev
        in_voting_mode = False

        # get the current articles
        current_articles = await self.loop.run_in_executor(
            self.executor,
            workers.get_arxiv_listing,
        )

        # if there aren't any articles for the latest date, show an error
        if current_articles['ntotal'] == 0:

            message = (
                "Sorry, we can't find any arXiv astro-ph articles for "
                "the requested date: %s" % current_articles['utcdate']
            )

            self.render_page_not_found(message)

        # otherwise, show the listing based on the value of in_voting_mode
        else:

            if in_voting_mode:

                await self.render(
                    'listing-voting-active.html',
                    baseurl=self.conf.base_url,
                    current_user=self.current_user,
                    conf=self.conf,
                    page_title=(
                        'Vote on papers for %s' %
                        current_articles['utcdate'].strftime('%A, %B %d %Y')
                    ),
                    flash_message_list=self.flash_message_list,
                    alert_type=self.alert_type,
                    current_articles=current_articles,
                )

            else:

                await self.render(
                    'listing-voting-inactive.html',
                    baseurl=self.conf.base_url,
                    current_user=self.current_user,
                    conf=self.conf,
                    page_title=(
                        'Papers for %s' %
                        current_articles['utcdate'].strftime('%A, %B %d %Y')
                    ),
                    flash_message_list=self.flash_message_list,
                    alert_type=self.alert_type,
                    current_articles=current_articles,
                )


class ArchiveIndexHandler(basehandler.BaseHandler):

    async def get(self):
        '''This handles the article listings and switches between voting
        and list mode.

        Also handles the main arxiv section and the archive listings.

        '''

        # get the list of local authors
        paper_archives = await self.loop.run_in_executor(
            self.executor,
            workers.get_coffee_archive,
        )

        self.render(
            'archive-index.html',
            baseurl=self.conf.base_url,
            current_user=self.current_user,
            conf=self.conf,
            page_title='Astro-Coffee@%s' % self.conf.institution_short_name,
            flash_message_list=self.flash_message_list,
            alert_type=self.alert_type,
            paper_archives=paper_archives,
        )


class ArchiveListingHandler(basehandler.BaseHandler):

    async def get(self, listing_date):
        '''This handles the article listings and switches between voting
        and list mode.

        Also handles the main arxiv section and the archive listings.

        '''

        utcdate = xhtml_escape(listing_date)

        # get the current articles
        execfn = partial(
            workers.get_arxiv_listing,
            utcdate=utcdate,
            for_archive_listing=True
        )

        current_articles = await self.loop.run_in_executor(
            self.executor,
            execfn,
        )

        if current_articles['ntotal'] == 0:
            message = (
                "Sorry, we can't find any arXiv astro-ph articles for "
                "this requested date."
            )
            self.render_page_not_found(message)

        else:
            await self.render(
                'listing-archive.html',
                baseurl=self.conf.base_url,
                current_user=self.current_user,
                conf=self.conf,
                page_title=(
                    'Papers for %s' %
                    current_articles['utcdate'].strftime('%A, %B %d %Y')
                ),
                flash_message_list=self.flash_message_list,
                alert_type=self.alert_type,
                current_articles=current_articles,
            )
