#!/bin/bash
bash server-stop.sh
git pull
sudo python setup.py install
bash server-start.sh
