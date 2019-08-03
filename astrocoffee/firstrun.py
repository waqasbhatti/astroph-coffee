# -*- coding: utf-8 -*-

'''This sets up the basedir for the coffee-server.

- copies over the conf file to the basedir and updates it
- makes the authnzerver auth DB
- makes the astro-coffee DB
- copies over the template subdir to the basedir
- copies over the static directory to the basedir

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

import os
import os.path
