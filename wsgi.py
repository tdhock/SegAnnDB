import sys
sys.path.insert(0, "/home/th798/lib/python2.7/site-packages")
print sys.path
from pyramid.paster import get_app
application = get_app('/build/SegAnnDB/production.ini', 'main')

