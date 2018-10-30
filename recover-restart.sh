#!/bin/bash
export PYTHONPATH=.:~/lib/python2.7/site-packages/
pkill -9 python
db_recover -h db
python process_daemon.py &
python learn_daemon.py &
##python ~/lib/python2.7/old-packages/pyramid/scripts/pserve.py --reload development.ini
pserve --reload development.ini
