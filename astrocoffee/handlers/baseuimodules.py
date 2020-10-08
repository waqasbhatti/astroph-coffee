# -*- coding: utf-8 -*-

'''These are the base UI modules to be used with the BaseHandler.

'''

#############
## LOGGING ##
#############

import logging
LOGGER = logging.getLogger(__name__)


#####################
## TORNADO IMPORTS ##
#####################

import tornado.web


################
## UI MODULES ##
################

class LoginBoxModule(tornado.web.UIModule):
    '''
    This is a UI module for showing a login box.

    This works with the loginbox-uimodule.html template.

    '''

    def render(self,
               baseurl='',
               current_user=None):
        '''This returns a login box UI module.

        baseurl is the base URL of the server. This should not end with '/'.

        current_user is a dict used by the BaseHandler above
        (self.current_user).

        '''

        if (current_user and
            current_user.get('user_role') and
            current_user['user_role'] == 'authenticated'):

            boxmode = 'signedin'
            current_user_name = (
                current_user.get('full_name') or
                current_user.get('email') or
                ''
            )

        elif (current_user and
              current_user.get('user_role') and
              current_user['user_role'] in ('superuser','staff')):

            boxmode = 'admin'
            current_user_name = (
                current_user.get('full_name') or
                current_user.get('email') or
                ''
            )

        else:

            boxmode = 'normal'
            current_user_name = ''

        return self.render_string(
            "loginbox-uimodule.html",
            boxmode=boxmode,
            baseurl=baseurl,
            current_user_name=current_user_name,
        )


class FlashMessageModule(tornado.web.UIModule):
    '''This is a UI module for showing a flash message.

    Works with flashmessage-uimodule.html template.

    '''

    def render(self,
               flash_message_list=None,
               alert_type=None):
        '''
        This returns a login box UI module.

        alert_type is one of: warning, danger, info, primary, secondary, success

        flash_message_list is a list of messages to render separated by
        message_separator.

        '''

        if not alert_type:
            return ''

        if not flash_message_list:
            flash_messages = None
        else:
            flash_messages = '<br>'.join(flash_message_list)

        return self.render_string(
            "loginbox-uimodule.html",
            flash_messages=flash_messages,
            alert_type=alert_type,
        )
