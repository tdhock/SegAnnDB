import sys
import csv
import os
import urllib

user = sys.argv[1]
server = sys.argv[2]
os.mkdir('downloaded_profiles')
with open('trimmed.csv','r') as csvfile:
    filereader = csv.reader(csvfile)
    for line in filereader:
        urllib.urlretrieve('http://' + server + '/export/' + user + '/' + line[0] + '/breaks/bed/', 'downloaded_profiles/' + line[0] + '.bed')
        with open('downloaded_profiles/' + line[0] + '.bed', 'r') as bed_read:
            beddata = bed_read.read()
        beddata = '\n'.join(beddata.split('\n')[1:-1])
        beddata = beddata.replace(' ','\t')
        print beddata
        with open('downloaded_profiles/' + line[0] + '.bed', 'w') as bed_write:
            bed_write.write(beddata)

