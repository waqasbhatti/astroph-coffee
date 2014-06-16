#!/bin/bash

BINDIR=$1

source $BINDIR/bin/activate

# install latest versions of needed packages
pip install tornado -U
pip install passlib -U
pip install requests -U
pip install BeautifulSoup4 -U
pip install lxml -U
pip install selenium -U
pip install pytz

deactivate
