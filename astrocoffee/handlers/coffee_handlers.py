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

        flash_message_list, alert_type = self.get_flash_messages()

        self.render(
            'index.html',
            baseurl=self.conf.base_url,
            current_user=self.current_user,
            conf=self.conf,
            page_title='Astro-Coffee@%s' % self.conf.institution_short_name,
            flash_message_list=flash_message_list,
            alert_type=alert_type,
        )


class LocalAuthorListHandler(basehandler.BaseHandler):

    async def get(self):
        '''
        This handles the local author list page.

        '''

        flash_message_list, alert_type = self.get_flash_messages()

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
            flash_message_list=flash_message_list,
            alert_type=alert_type,
            local_authors=local_authors,
            author_list=author_list
        )


class AboutHandler(basehandler.BaseHandler):

    def get(self):
        '''
        This handles the about page.

        '''

        flash_message_list, alert_type = self.get_flash_messages()

        self.render(
            'about-page.html',
            baseurl=self.conf.base_url,
            current_user=self.current_user,
            conf=self.conf,
            page_title='About the astro-coffee server',
            flash_message_list=flash_message_list,
            alert_type=alert_type,
        )


class ArticleListingHandler(basehandler.BaseHandler):

    async def get(self):
        '''This handles the article listings and switches between voting
        and list mode.

        Also handles the main arxiv section and the archive listings.

        '''

        flash_message_list, alert_type = self.get_flash_messages()

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
                flash_message_list=flash_message_list,
                alert_type=alert_type,
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
                flash_message_list=flash_message_list,
                alert_type=alert_type,
                current_articles=current_articles,
            )


class ArchiveIndexHandler(basehandler.BaseHandler):

    async def get(self):
        '''This handles the article listings and switches between voting
        and list mode.

        Also handles the main arxiv section and the archive listings.

        '''

        flash_message_list, alert_type = self.get_flash_messages()

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
            flash_message_list=flash_message_list,
            alert_type=alert_type,
            paper_archives=paper_archives,
        )


class ArchiveListingHandler(basehandler.BaseHandler):

    async def get(self, listing_date):
        '''This handles the article listings and switches between voting
        and list mode.

        Also handles the main arxiv section and the archive listings.

        '''

        flash_message_list, alert_type = self.get_flash_messages()

        self.render(
            'index.html',
            baseurl=self.conf.base_url,
            current_user=self.current_user,
            conf=self.conf,
            page_title='Astro-Coffee@%s' % self.conf.institution_short_name,
            flash_message_list=flash_message_list,
            alert_type=alert_type,
        )
