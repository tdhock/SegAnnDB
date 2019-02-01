# The best web browser for viewing SegAnnDB is an
# old version of google chrome, ca Mar 2013 - Jan 2014.
# http://google-chrome.en.uptodown.com/ubuntu/download/65857

# Download python-dev and required packages.
sudo apt-get install python-dev python-setuptools python-numpy python-bsddb3 subversion build-essential python-imaging db-util git

# These are not strictly essential, but are useful:
sudo apt-get install emacs htop 

# Download/install pyramid + persona
sudo easy_install "pyramid==1.4.5" 
sudo easy_install "pyramid-persona==1.5"

# Download and install SegAnnot and PrunedDP extension modules.
cd
svn checkout svn://r-forge.r-project.org/svnroot/segannot/python segannot
##or: git clone https://github.com/rforge/segannot.git
cd segannot
python setup.py build
sudo python setup.py install

# Download/install SegAnnDB.
if [ "$TRAVIS" = "true" ]; then
    cd $TRAVIS_BUILD_DIR
else
    cd
    git clone https://github.com/tdhock/SegAnnDB.git
    cd SegAnnDB
fi
sed -i 's#^FILE_PREFIX.*$#FILE_PREFIX = "/var/www"#' plotter/db.py
sudo python setup.py install

# for an apache web server
sudo apt-get install apache2 libapache2-mod-wsgi
cd /var/www
sudo chown www-data .
sudo -u www-data mkdir db secret chromlength
if [ "$TRAVIS" = "true" ]; then
    sudo cp $TRAVIS_BUILD_DIR/apache.config \
        /etc/apache2/sites-available/pyramid.conf
else
    sudo cp ~/SegAnnDB/apache.config /etc/apache2/sites-available/pyramid.conf
fi
sudo a2enmod wsgi
sudo a2dissite 000-default
sudo a2ensite pyramid
if [ "$TRAVIS" = "true" ]; then
    cd $TRAVIS_BUILD_DIR
else
    cd ~/SegAnnDB
fi
bash server-recover-restart.sh
# edit  production.ini: set public server name for persona! (NO TRAILING slash)
# edit /etc/apache2/sites-available/pyramid.conf: add ServerName xxx.xxx.xxx.xxx
sudo wget -O /var/www/chromlength/hg19.txt.gz http://hgdownload.soe.ucsc.edu/goldenPath/hg19/database/chromInfo.txt.gz

# start the local server and 2 daemons (profile processing and
# learning).
mkdir db secret chromlength
bash recover-restart.sh &
