#!/bin/bash

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

python -c 'import arxivutils, arxivdb; x = arxivutils.arxiv_update(fakery=False); arxivdb.insert_articles(x)'

deactivate

echo "arxiv update ended at: " `date`
cd -

