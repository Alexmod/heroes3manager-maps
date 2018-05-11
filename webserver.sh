#!/bin/bash

HOME=/home/hero
VENVDIR=$HOME/env/bin
BINDIR=$HOME/www

cd $BINDIR
source $VENVDIR/activate
/home/hero/env/bin/gunicorn  -b localhost:8001  main:app 
