#!/bin/bash
sudo /etc/init.d/apache2 stop
sudo -u www-data pkill -9 python
sudo -u www-data rm -rf /var/www/db/*
sudo -u www-data python process_daemon.py &
sudo -u www-data python learn_daemon.py &
sudo /etc/init.d/apache2 start