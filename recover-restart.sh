#!/bin/bash
export PYTHONPATH=.:~/lib/python2.7/site-packages/
pkill -9 python
db_recover -h db
python process_daemon.py &
python learn_daemon.py &
pserve --reload development.ini
