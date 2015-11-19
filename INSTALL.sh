# The best web browser for viewing SegAnnDB is an
# old version of google chrome, ca Mar 2013 - Jan 2014.
http://google-chrome.en.uptodown.com/ubuntu/download/65857

# Download python-dev and required packages.
sudo apt-get install python-dev python-setuptools python-numpy python-bsddb3 subversion build-essential python-imaging db-util

# These are not strictly essential, but are useful:
sudo apt-get emacs htop 

# Download/install pyramid + persona
sudo easy_install "pyramid==1.4.5" 
sudo easy_install pyramid-persona

# Download and install SegAnnot and PrunedDP extension modules.
cd
svn checkout svn://r-forge.r-project.org/svnroot/segannot/python segannot
python setup.py build
sudo python setup.py install

# Download/install SegAnnDB.
cd
git clone https://github.com/tdhock/SegAnnDB.git
cd SegAnnDB
sed -i 's/^FILE_PREFIX =/#FILE_PREFIX =/' plotter/db.py
sed -i 's/#FILE_PREFIX = "."/FILE_PREFIX = "."/' plotter/db.py
sudo python setup.py install

# for an apache web server
sudo apt-get install apache2 libapache2-mod-wsgi
cd /var/www
mkdir db secret chromlength
cp ~/SegAnnDB/apache.config /etc/apache2/sites-available/pyramid.conf
sudo a2enmod wsgi
sudo a2dissite 000-default
sudo a2ensite pyramid
cd ~/SegAnnDB
bash server-recover-restart.sh

# start the local server and 2 daemons (profile processing and
# learning).
mkdir db secret chromlength
bash recover-restart.sh
