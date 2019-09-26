#!/bin/bash
set -o errexit
bash server-stop.sh
##git pull
sudo python setup.py install
bash server-start.sh
