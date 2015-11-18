import requests
import getpass
import re

BASE_URL = "http://bioviz.rocq.inria.fr/plotter"
LOGIN_URL = BASE_URL+"/login/"
ADD_URL_ITEMS = [
    BASE_URL,
    "profile",
    "%(profile_id)s",
    "%(chromosome)s",
    "add_region",
    "%(type)s",
    "%(annotation)s",
    "%(min)s",
    "%(max)s",
    #"?profiles=%(profile_id)s&chromosomes=%(chromosome)s",
    "", # faster.
    ]
ADD_URL = "/".join(ADD_URL_ITEMS)

def get_sessionid(user):
    password = getpass.getpass("Password for %s:"%user)
    post_data = {
        "username":user,
        "password":password,
        }
    #print post_data
    r=requests.post(LOGIN_URL,data=post_data)
    if r.status_code == 403:
        #print r.text
        raise ValueError("http 403 password incorrect")
    ##print r.cookies
    sid = r.cookies["sessionid"]
    return sid

def upload_region(sessionid,region_info):
    url = ADD_URL % region_info
    cookies = {"sessionid":sessionid}
    r = requests.get(url,cookies=cookies)
    if r.status_code != 200:
        raise ValueError("http not 200 for "+url)
    return r.json

def csv2regions(csv_filename):
    f = open(csv_filename)
    header = f.readline()[:-1]
    variables = header.split(',')
    return [dict(zip(variables,l[:-1].split(','))) for l in f]

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print "Usage: %s user regions.csv"%sys.argv[0]
        sys.exit(1)
    cmd, user, regions_file = sys.argv
    regions = csv2regions(regions_file)
    sid = get_sessionid(user)
    n = len(regions)
    nlen = len(str(n))
    format = "%"+str(nlen+1)+"s"
    status = format + " / " + format + " uploading region on pid%s chr%s "
    for i,r in enumerate(regions):
        print status%(i+1,n,r["profile_id"],r["chromosome"])
        upload_region(sid,r)
        
