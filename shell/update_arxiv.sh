#!/bin/bash

# This is meant to run as a cronjob.
# Example cronjob format (runs Sunday through Thursday at 20:19):
# 19 20 * * 0,1,2,3,4 /path/to/astroph-coffee/shell/update_arxiv.sh \
# /path/to/astroph-coffee > \
# /path/to/astroph-coffee/run/logs/arxiv-auto-update.log 2>&1


if [ $# -lt 1 ]
then
    echo "Usage: $0 <astroph-coffee basepath>"
    exit 2
fi


BASEPATH=$1

echo "arxiv update started at:" `date`
echo "astro-coffee server directory: $BASEPATH"

cd $BASEPATH/run
source $BASEPATH/run/bin/activate

# fakery = False means one can run this on a headless server
python -c 'import arxivutils, arxivdb; x = arxivutils.arxiv_update(fakery=False); arxivdb.insert_articles(x,fullname_match_threshold=72,firstname_match_threshold=93)'

deactivate

echo "arxiv update ended at: " `date`
cd -
