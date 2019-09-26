#!/bin/bash
set -o errexit
sudo -u apache db_recover -h /var/www/db
sudo -u apache python process_daemon.py &
sudo -u apache python learn_daemon.py &
sudo /sbin/httpd -k start
