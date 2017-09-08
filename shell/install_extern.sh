#!/bin/bash

BINDIR=$1

source $BINDIR/bin/activate

# install latest versions of needed packages
pip install tornado -U
pip install requests -U
pip install BeautifulSoup4 -U
pip install selenium -U
pip install pytz -U
pip install itsdangerous -U
pip install geoip2 -U
pip install py2-ipaddress -U

deactivate
