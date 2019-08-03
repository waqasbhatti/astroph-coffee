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
import secrets
from datetime import datetime
import tempfile
import shutil
import glob

import requests

from authnzerver import secrets as authsecrets

from . import database
from . import modtools
from . import arxiv


###############
## CONF PREP ##
###############

def prepare_conf_file(basedir):
    '''
    This prepares the conf file.

    '''

    moddir = os.path.dirname(os.path.abspath(__file__))
    confmod = os.path.join(moddir, 'conftemplate.py')

    # read the conf file
    with open(confmod, 'r') as infd:
        conf = infd.read()

    # replace the basedir string
    conf = conf.replace('{{ basedir }}', os.path.abspath(basedir))

    # generate a session secret
    session_secret = secrets.token_urlsafe(32)
    conf = conf.replace('{{ session_secret }}', session_secret)

    # write the conf to the basedir
    out_conffile = os.path.join(os.path.abspath(basedir),
                                'coffee_settings.py')

    if not os.path.exists(basedir):
        os.makedirs(basedir)

    with open(out_conffile,'w') as outfd:
        outfd.write(conf)

    # verify everything's OK with the conf module
    conf = modtools.module_from_string(out_conffile, force_reload=True)

    if conf is not None:
        del conf
        LOGINFO("New astro-coffee server config file generated: %s" %
                out_conffile)
        return out_conffile
    else:
        LOGERROR("Could not verify the conf file: %s" % out_conffile)
        return None


####################
## DATABASE SETUP ##
####################

def setup_databases(conf_file):
    '''
    This sets up the auth and astro-coffee databases.

    '''

    conf = modtools.module_from_string(conf_file, force_reload=True)

    LOGINFO("Making the astro-coffee database...")

    # create the astrocoffee DB
    coffeedb_path = database.new_astrocoffee_db(conf.database_url)

    LOGINFO("Making the authentication server database...")

    # create the auth DB and credentials in the basedir
    authdb_path, creds, _ = authsecrets.autogen_secrets_authdb(conf.basedir)

    return coffeedb_path, authdb_path, creds


def get_geolite2_db(basedir):
    '''
    This gets the GeoLite2 database from MaxMind.

    '''

    url = (
        "https://geolite.maxmind.com/download/geoip/database/"
        "GeoLite2-City.tar.gz"
    )

    LOGINFO("Fetching new MaxMind GeoLite2-City IP-geolocation DB...")
    resp = requests.get(url, stream=True)

    outfile = os.path.join(basedir, 'GeoLite2-City.mmdb')

    with tempfile.TemporaryDirectory() as tempdir:

        dlfile = os.path.join(tempdir, 'GeoLite2-City.tar.gz')

        with open(dlfile, 'wb') as outfd:
            for chunk in resp.iter_content(chunk_size=8096):
                outfd.write(chunk)

        shutil.unpack_archive(dlfile, tempdir, 'gztar')
        path_to_mmdb_dir = glob.glob(os.path.join(tempdir,
                                                  'GeoLite2-City_2*'))
        path_to_mmdb_file = os.path.join(path_to_mmdb_dir[0],
                                         'GeoLite2-City.mmdb')
        if os.path.exists(path_to_mmdb_file):
            shutil.copy(path_to_mmdb_file, outfile)

    return outfile


#######################
## ROLL UP FUNCTIONS ##
#######################

def setup_coffee_server(basedir, nodb=False):
    '''This rolls up all functions above and returns the path to the conf file.

    Also makes a .coffee-first-run-done file in the basedir to indicate setup is
    complete.

    '''

    conf_file = prepare_conf_file(basedir)

    if not nodb:

        # set up the coffee DB
        coffeedb_path, authdb_path, creds = setup_databases(conf_file)

        # get a listing
        conf = modtools.module_from_string(conf_file, force_reload=True)
        arxivdict = arxiv.fetch_arxiv_listing()
        if arxivdict:
            arxiv.insert_arxiv_listing((conf.database_url,
                                        database.ASTROCOFFEE),
                                       arxivdict)

    # get the GeoLite2 DB
    get_geolite2_db(basedir)

    with open(os.path.join(basedir, '.coffee-first-run-done'), 'w') as outfd:
        outfd.write('Completed at %sUTC\n' % datetime.utcnow())

    return conf_file
