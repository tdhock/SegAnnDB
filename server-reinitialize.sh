#!/bin/bash
bash server-stop.sh
sudo -u apache rm -rf /var/www/db/*
bash server-start.sh
