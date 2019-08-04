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


class CoffeeHandler(basehandler.BaseHandler):

    def get(self):
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
