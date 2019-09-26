#!/bin/bash
set -o errexit
sudo /sbin/httpd -k stop
sudo -u apache pkill -9 python
