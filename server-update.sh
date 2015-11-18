#!/bin/bash
bash server-stop.sh
svn up
sudo python setup.py install
bash server-start.sh