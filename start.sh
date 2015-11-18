#!/bin/bash
rm env/* && pkill -9 python && python process_profiles.py & PYTHONPATH=.:~/lib/python2.7/site-packages/ pserve --reload development.ini
