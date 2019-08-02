# -*- coding: utf-8 -*-

'''This is the configuration file template for astro-coffee.

'''

import os.path

####################
## BASIC SETTINGS ##
####################

# The server will place its files in the base directory. All other paths are
# relative to this directory.
basedir = '{{ basedir }}'

# This is where the server keeps the page templates. Edit these to change the
# various UI elements of the webpages.
template_path = os.path.join(basedir, 'templates')

# This is where the server keeps its JS and CSS files. Edit the CSS files in
# {asset_path}/css/astrocoffee.css as necessary
asset_path = os.path.join(basedir, 'static')

# This defines the number of background workers used by the server.
max_workers = 2

# This defines the TCP port on which the server listens.
server_port = 5005

# This defines the address on which the server listens. 0.0.0.0 means it listens
# on all interfaces, 127.0.0.1 means it only listens for connections from
# localhost.
server_address = '0.0.0.0'


####################
## AUTHENTICATION ##
####################

# This is the SQLAlchemy database URL for the database tracking users, logins,
# signups, etc.
authdb_url = 'sqlite:///%s' % os.path.join(basedir,'authdb.sqlite')


###############
## DATABASES ##
###############

# This is the SQLAlchemy database URL for the main astro-coffee database.
database_url = 'sqlite:///%s' % os.path.join(basedir,'astro-coffee.sqlite')


############
## PEOPLE ##
############

# These are the contact details of the person responsible for this server.
admin_name = 'Admin Contact'
admin_email = 'coffeeadmin@institution.edu'


############
## PLACES ##
############

# The name of room where Astro Coffee happens.
room = 'Example Room'

# The name of building where Astro Coffee happens.
building = 'Example Hall'

# The name of department where Astro Coffee happens.
department = 'Department of Astronomy'

# The name of institution where Astro Coffee happens.
institution = 'Example University'


###########
## TIMES ##
###########

# This is the timezone where the astro-coffee server is located in. used to
# handle times when no listings are available yet, and convert times below to
# UTC (used for scheduling updates, and opening/closing voting windows). The
# timezone below must be in the Olson TZ database
# (http://en.wikipedia.org/wiki/Tz_database).
server_tz = 'America/New_York'

# The default voting start time is 20:45 local time.
voting_start_localtime = '20:45'

# The default voting cutoff time is 10:29 in the morning.
voting_end_localtime = '10:29'

# Astro Coffee at Princeton is at 10:30 in the morning.
coffee_at_localtime = '10:30'

# This sets how long to keep a paper in the reserved list.
reserve_interval_days = 5


####################
## ACCESS CONTROL ##
####################

# This is the path to the MaxMind GeoIP2 city database used for IP address
# location and geofencing of voting attempts. Download updates from:
# http://dev.maxmind.com/geoip/geoip2/geolite2/.
geoip_database = os.path.join(basedir, 'GeoLite2-City.mmdb')

# These are ISO codes for countries and subdivisions from where voting is
# allowed (http://en.wikipedia.org/wiki/ISO_3166-2).
allowed_countries = 'US'
allowed_subdivisions = 'NJ, NY, PA'

# These are IP address range definitions in CIDR format (comma-separated)
# https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing#CIDR_notation.
# These are used to make sure certain IPs can always vote. Look these up for
# your institution using https://ipinfo.io/ (find the AS number and click on it
# to get the IP address ranges associated with it).
voting_cidr = {
    '128.0.0.0/8',
    '10.0.0.0/4',
}

# These are IP address range definitions for users that will have reserving
# permissions. These should be ideally restricted to the department only.
reserve_cidr = {
    '128.0.0.0/8',
    '10.0.0.0/4',
}

# These are IP address range definitions for users that will sign up to present
# papers. These should be ideally restricted to the department only.
present_cidr = {
    '128.0.0.0/8',
    '10.0.0.0/4',
}

# These are IP address range definitions for users that will have edit
# permissions. These should be ideally restricted to the department only.
edit_cidr = {
    '128.0.0.0/8',
    '10.0.0.0/4',
}

# These are the email address domain names for which signups are allowed.
email_domains = {
    'astro.institution.edu',
    'physics.institution.edu',
    'otherinstitute.edu',
}

###################
## LOCAL AUTHORS ##
###################

# this is the path to the local authors CSV that will be used to initially
# populate the list of local authors. this should contain rows in the following
# format:
#
# author_name,author_email,author_special_affiliation
#
# author_special_affiliation can be an empty string to indicate the author is
# associated with the main group of people that'll be using the server. If the
# author belongs to another institution but should be counted as a local author,
# include that institution's name in this column.
local_author_csv = os.path.join(basedir, 'local-authors.csv')
