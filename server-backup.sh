bash server-stop.sh
pushd /var/www
sudo -u www-data cp -r db secret /home/www-data/backup
popd
bash server-start.sh
