#!/usr/bin/python
import requests
import pdb
import re
import gzip

to_check = [
    ("share","public|private|[a-z.]+"),
    ("export","yes|no"),
    ("name","[-a-zA-Z0-9]+"),
    ("type","bedGraph"),
    ("maxSegments","[0-9]+"),
    ("db","[a-zA-Z0-9]+"),
    ]
header_regexes = {}
for var, pattern in to_check:
    regex = "%s=(%s)"%(var,pattern)
    header_regexes[var] = (regex,re.compile(regex))

line_patterns = [
    "(?P<chromosome>[0-9a-zA-Z]+)",
    "(?P<chromStart>[0-9]+)",
    "(?P<chromEnd>[0-9]+)",
    r"(?P<logratio>\S+)",
    ]
column_sep = r'\s+'
line_pattern = "^%s$"%column_sep.join(line_patterns)
line_regex = re.compile(line_pattern)

error_regex = re.compile(r"<pre>\n([^<]+)")

def check_file(f):
    """Reality checks for valid profile data files.

    Raises an exception if there was a problem with the file.

    """
    f.seek(0)
    header = f.readline()
    hinfo = {}
    # check for several things in the header.
    for var,(pattern,regex) in header_regexes.iteritems():
        m = regex.search(header)
        if not m:
            raise ValueError("header does not indicate '%s'"%pattern)
        hinfo[var] = m.groups()[0]
    # check each line for the correct format.
    for line in f:
        if not line_regex.match(line.strip()):
            print repr(line)
            raise ValueError("line\n%sdoes not match '%s'"%(
                    line,line_pattern))
    return hinfo

def upload_profile(filename,user,upload_url):
    """Upload one profile data file to the server.

    Raises an exception if something went wrong.

    filename can indicate either a plain text or gzipped bedGraph text
    file. We will gzip it before sending it to the server.

    bedGraph format files can be constructed easily, see
    http://genome.ucsc.edu/goldenPath/help/bedgraph.html
    
    """
    try:
        f = gzip.open(filename)
        header = f.readline()
        gz_name = filename
    except IOError: #must be plain text, so gzip it
        f = open(filename)
        gz_name = filename + ".gz"
        print "compressing %s to %s."%(filename,gz_name)
        gz = gzip.open(gz_name,"w")
        for line in f:
            gz.write(line)
        gz.close()
    # by now gz_name is the compressed filename to send to the server,
    # and f is a file open in text read mode.
    hinfo = check_file(f)
    # now construct the post request.
    f = open(gz_name,"rb")
    files = {"file":f}
    post_data = {"user":user}
    r = requests.post(upload_url,files=files,data=post_data)
    if r.status_code != 200:
        raise ValueError("http error %s"%r.status_code)
    m = error_regex.search(r.text)
    if m:
        raise ValueError(m.groups()[0])
    success_msg = "Profile %(name)s has passed checks" % hinfo
    if success_msg not in r.text:
        f=open("response.html", "w")
        f.write(r.text)
        f.close()
        raise ValueError("wrote non-standard response to response.html")
    return hinfo
    
if __name__ == "__main__":
    import webbrowser
    import sys
    if len(sys.argv) < 4:
        print "Usage: %s http://seganndb.domain user probes.bedGraph(.gz)? ..."%sys.argv[0]
        sys.exit(1)
    url = sys.argv[1]
    user = sys.argv[2]
    successful_uploads = 0
    for fn in sys.argv[3:]:
        try:
            hinfo = upload_profile(fn,user,url+"/upload")
            print "%s: uploaded as %s."%(fn,hinfo["name"])
            successful_uploads += 1
        except Exception, e:
            # catch the exception and move on to the next file if possible.
            print '%s: ERROR: %s'%(fn,e)
    if successful_uploads > 0:
        webbrowser.open(url)
