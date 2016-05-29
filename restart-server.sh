#!/bin/bash
export PYTHONPATH=.:~/lib/python2.7/site-packages/
pkill -9 python
#rm env/*
#db_recover -h env
python process_daemon.py &
pserve --reload development.ini
