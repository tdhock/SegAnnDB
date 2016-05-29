sudo -u www-data db_recover -h /var/www/db
sudo -u www-data python process_daemon.py &
sudo -u www-data python learn_daemon.py &
sudo /etc/init.d/apache2 start
