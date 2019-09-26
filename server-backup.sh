#!/bin/bash
set -o errexit
bash server-stop.sh
PREFIX=/var/www
BACKUP=$PREFIX/backup
pushd $PREFIX
sudo -u apache mkdir -p $BACKUP
sudo -u apache cp -r db secret $BACKUP
popd
bash server-start.sh
