import cPickle as pickle
import gzip
import re
import os
import csv
import urllib2
import numpy
import math
import atexit
import time
# third party module not by me:
import bsddb3
# modules by me created specifically for this project:
from PrunedDP import PrunedDP
from SegAnnot import SegAnnotBases
from gradient_descent import mmir
import scatterplot
#import for image splitting
from PIL import Image
# scatterplot sizes in pixels.
# DEFAULT_WIDTH = 1500
DEFAULT_WIDTH = 1250
HEIGHT_PX = 200
CHROME_UBUNTU_MAX = 1000000
CHROME_WINDOWS_MAX = 300000
IPAD_MAX = 20000
# stuff for checking uploaded files.
HEADER_TUPS = [
    ("share", "[^ ]+"),
    ("export", "yes|no"),
    ("name", "[-a-zA-Z0-9]+"),
    ("type", "bedGraph"),
    ("maxSegments", "[0-9]+"),
    ("db", "hg1[789]"),
    ]
HEADER_PATTERNS = dict(HEADER_TUPS)
NAME_REGEX = re.compile(HEADER_PATTERNS["name"])

TO_COMPILE = [(var, "%s=(%s) " % (var, pattern))
              for var, pattern in HEADER_TUPS]
# do not include quotes in parsed description.
TO_COMPILE.append(("description", '"([^"]+)"'))
HEADER_REGEXES = {}
for var, regex in TO_COMPILE:
    HEADER_REGEXES[var] = (regex, re.compile(regex))
LINE_PATTERNS = [
    "chr(?P<chromosome>[0-9XY]+)",
    "(?P<chromStart>[0-9]+)",
    "(?P<chromEnd>[0-9]+)",
    # the regexp that we use for validating the logratio column is
    # quite permissive: \S+ can match 213E-2 and also NaN,
    # but we check for NaN later so this is no problem.
    r"(?P<logratio>\S+)",
    ]

COLUMN_SEP = r'\s+'
LINE_PATTERN = "^%s$" % COLUMN_SEP.join(LINE_PATTERNS)
LINE_REGEX = re.compile(LINE_PATTERN)
FILE_PREFIX = "/var/www"
#FILE_PREFIX = "."
SECRET_DIR = os.path.join(FILE_PREFIX, "secret")
DB_HOME = os.path.join(FILE_PREFIX, "db")
CHROMLENGTH_DIR = os.path.join(FILE_PREFIX, "chromlength")


def secret_file(fn, ch = None):
    if ch is None:
        ch = ""
    m = NAME_REGEX.match(fn)
    name = fn[:m.end()]
    dirname = os.path.join(SECRET_DIR, name, ch)
    # print dirname
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
    return os.path.join(dirname, fn)


def scatterplot_file(name, ch, suffix, lr_min, lr_max, width, lengths=None):
    """
    Parameters -
    name - profile name
    ch - chromosome number
    suffix - zoom level etc
    lr_min - log ratio min
    lr_max - log ratio max
    width - width in px
    length - base pairs
    """
    fn = "%s_chr%s_%s.png" % (name, ch, suffix)
    #print "making %s" % fn
    info = ChromProbes(name, ch).get()
    if lengths is None:
        pinfo = Profile(name).get()
        lengths = ChromLengths(pinfo["db"])
    #print fn, md, len(info["logratio"])
    scatterplot.draw(info, secret_file(fn),
                     int(width), HEIGHT_PX,
                     float(lr_min), float(lr_max),
                     1, lengths[ch])
    return fn


def split_image(file_name, chr_num, profile_name, suffix, width):
    """
    Parameters-
    file_name - the file name
    chr_num - the chromosome number
    profile_name - the profile id
    suffix - the zoom level
    width - the width_px of the image
    """
    file_location = SECRET_DIR + "/" + profile_name + "/" + chr_num + "/" + file_name
    save_path = SECRET_DIR + "/" + profile_name + "/" + chr_num

    # now open the file
    im = Image.open(file_location)

    i = DEFAULT_WIDTH
    j = 1

    while i <= width:
        #print i
        box = (i - 1250, 0, i, 200)
        img = im.crop(box)
        fn = "%s_chr%s_%s_%d.png" % (profile_name, chr_num, suffix, j)
        final_path = save_path + "/" + fn
        img.save(final_path)
        j += 1
        i += 1250


def to_string(a):
    return pickle.dumps(a, 2)


def from_string(a):
    return pickle.loads(a)

# AVOID out of memory Locker errors using apt-get install db-util. We
# can run db_recover -h env from the command line to reset locks and
# lockers to zero. NOTE: we don't do this here, but instead do this
# before the server and daemons are started.

#os.system("db_recover -h %s"%DB_HOME)

env = bsddb3.db.DBEnv()
env.open(
    DB_HOME,
    bsddb3.db.DB_INIT_MPOOL |
    # bsddb3.db.DB_INIT_CDB|
    bsddb3.db.DB_INIT_LOCK |
    bsddb3.db.DB_INIT_TXN |
    bsddb3.db.DB_INIT_LOG |
    bsddb3.db.DB_CREATE)
# print "nlockers=%(nlockers)s"%env.lock_stat()

CLOSE_ON_EXIT = []

# this prevents lockers/locks from accumulating when python is closed
# normally, but does not prevent this when we C-c out of the server.


def close_db():
    for db in CLOSE_ON_EXIT:
        db.close()
    env.close()
atexit.register(close_db)

DB_CLASSES = []

class DB(type):
    """Metaclass for Resource objects"""
    def __init__(cls, name, bases, dct):
        """Called when Resource and each subclass is defined"""
        if "keys" in dir(cls):
            DB_CLASSES.append(cls)
            cls.filename = name
            cls.db = bsddb3.db.DB(env)
            if cls.RE_LEN:
                cls.db.set_re_len(cls.RE_LEN)
            cls.db.open(cls.filename, None, cls.DBTYPE,
                        bsddb3.db.DB_AUTO_COMMIT |
                        # bsddb3.db.DB_THREAD|
                        bsddb3.db.DB_CREATE)
            CLOSE_ON_EXIT.append(cls.db)

def rename_all(find, replace):
    for cls in DB_CLASSES:
        if all([k in cls.keys for k in find.keys()]):
            cls.rename_all(find, replace)

class Resource(object):
    __metaclass__ = DB
    DBTYPE = bsddb3.db.DB_BTREE
    RE_LEN = 0

    @classmethod
    def all(cls):
        return [cls(*tup).get() for tup in cls.db_key_tuples()]

    @classmethod
    def db_keys(cls):
        return cls.db.keys()

    @classmethod
    def db_key_tuples(cls):
        return [k.split(" ") for k in cls.db_keys()]

    def rename(self, **kwargs):
        """Read data for this key, delete that db entry, and save it under another key"""
        for k in kwargs:
            if k not in self.keys:
                raise ValueError(
                    "names of arguments must be db keys: " +
                    ", ".join([str(x) for x in self.keys]))
        data_dict = self.get()
        self.put(None)
        self.info.update(kwargs)
        self.values = tuple(self.info[k] for k in self.keys)
        self.set_db_key()
        self.put(data_dict)
    
    @classmethod
    def rename_all(cls, find, replace):
        """Call rename for all entries in this DB

        find is a dictionary used to search for entries in this DB;
        entry.rename(**replace) will be called for each of the entries
        found.

        """
        entry_list = []
        all_entries = cls.db_key_tuples()
        for tup in all_entries:
            entry = cls(*tup)
            match_list = [entry.info[k]==v for k,v in find.iteritems()]
            if all(match_list):
                entry_list.append(entry)
        print "%s %4d / %4d %s."%(
            cls.__name__,
            len(entry_list), 
            len(all_entries),
            "entry matches" if len(entry_list)==1 else "entries match",
        )
        for i, entry in enumerate(entry_list):
            old_db_key = entry.db_key
            entry.rename(**replace)
            print "%s %4d / %4d '%s' -> '%s'"%(
                cls.__name__, 
                i+1,
                len(entry_list),
                old_db_key, 
                entry.db_key,
            )

    @classmethod
    def has_key(cls, k):
        return k in cls.db

    def __init__(self, *args):
        if len(args) != len(self.keys):
            raise ValueError(
                "should have exactly %d args: %s"%(
                    len(self.keys),
                    ", ".join([str(x) for x in self.keys]),
                              ))
        self.values = [str(a) for a in args]
        for a in self.values:
            if " " in a:
                raise ValueError("values should have no spaces")
        self.info = dict(zip(self.keys, self.values))
        self.set_db_key()

    def set_db_key(self):
        self.db_key = " ".join([str(x) for x in self.values])

    def alter(self, fun):
        """Apply fun to current value and then save it.

        """
        txn = env.txn_begin()
        before = self.get(txn)
        after = fun(before)
        self.put(after, txn)
        txn.commit()
        return after

    def get(self, txn=None):
        if self.db_key not in self.db:
            return self.make(txn)
        val = self.db.get(self.db_key, txn=txn)
        return from_string(val)

    def make(self, txn=None):
        made = self.make_details()
        self.put(made, txn)
        return made

    def put(self, value, txn=None):
        if value is None:
            if self.db_key in self.db:
                self.db.delete(self.db_key, txn=txn)
        else:
            self.db.put(self.db_key, to_string(value), txn=txn)

    def __repr__(self):
        return '%s("%s")' % (self.__class__.__name__, self.db_key)

    def make_details(self):
        return None


class Container(Resource):

    """Methods to support updating lists or dicts."""

    def add(self, item):
        self.item = item
        after = self.alter(self.add_item)
        return self.item, after

    def remove(self, item):
        self.item = item
        after = self.alter(self.remove_item)
        return self.removed, after


class ResList(Container):

    """Methods for updating stored lists."""

    def add_item(self, L):
        L.insert(0, self.item)
        return L

    def remove_item(self, L):
        if self.item in L:
            i = L.index(self.item)
            self.removed = L.pop(i)
        else:
            self.removed = None
        return L


class UserError(Container):

    """Each UserError is a dict with keys corresponding to chroms that
    have been annotated since the last learning."""
    keys = ("user", )

    def add_item(self, D):
        pro, ch, err = self.item
        D[(pro, ch)] = err
        return D

    def make_details(self):
        return {}


class Regions(Container):

    """Dict of annotated regions."""

    def add_item(self, D):
        self.item["id"] = D["next"]
        self.item["mid"] = (self.item["min"]+self.item["max"])/2
        D["data"][D["next"]] = self.item
        D["next"] += 1
        return D

    def remove_item(self, D):
        self.removed = D["data"].pop(self.item)
        return D

    def make_details(self):
        return {"next": 0, "data": {}}

    def count(self):
        return len(self.get()["data"])

    def json(self):
        return self.get()["data"].values()

    def key_min(self):
        return [(k, d["min"]) for k, d in self.get()["data"].iteritems()]


class ChromLengths(Resource):
    CHROM_ORDER = [str(x+1) for x in range(22)]+["X"]
    CHROM_RANK = dict(zip(CHROM_ORDER, enumerate(CHROM_ORDER)))
    keys = ("db", )
    u = "http://hgdownload.soe.ucsc.edu/goldenPath/%s/database/chromInfo.txt.gz"

    def make_details(self):
        s = self.values[0]
        local = os.path.join(CHROMLENGTH_DIR, s+".txt.gz")
        if not os.path.isfile(local):
            # print "downloading %s" % local
            #u = self.u % s
            #urllib2.urlopen(u, local)
            # print "chrom info for %s not available"%s
            return None
        # print "reading %s" % local
        f = gzip.open(local)
        r = csv.reader(f, delimiter="\t")
        chroms = dict([
            (ch.replace("chr", ""), int(last))
            for ch, last, ignore in r
            ])
        return dict([
            (ch, chroms[ch])
            for ch in self.CHROM_ORDER
            ])


def get_model(probes, break_after):
    """Calculate breaks and segments after PrunedDP."""
    break_min = probes["chromStart"][break_after]
    break_max = probes["chromStart"][break_after+1]
    break_mid = (break_min+break_max)/2
    begin_slice = [0]+(break_after+1).tolist()
    end_slice = (break_after+1).tolist()+[len(probes["logratio"])]
    yi = [probes["logratio"][b:e] for b, e in zip(begin_slice, end_slice)]
    assert sum([len(y) for y in yi]) == len(probes["logratio"])
    mean = [y.mean() for y in yi]
    residuals = [y-mu for y, mu in zip(yi, mean)]
    first_base = [probes["chromStart"][0]]+break_mid.tolist()
    last_base = break_mid.tolist()+[probes["chromStart"][-1]]
    # convert types to standard python types, otherwise we get json
    # error.
    segments = [
        {"logratio": float(m), "min": int(f), "max": int(l)}
        for m, f, l in zip(mean, first_base, last_base)
        ]
    json = {
        "breakpoints": tuple([
            {"min": int(m), "position": int(p), "max": int(M)}
            for m, p, M in zip(break_min, break_mid, break_max)
            ]),
        "segments": tuple(segments),
        }
    return {
        # for quickly checking model agreement to annotated regions.
        "breaks": numpy.array(break_mid),
        "json": json,
        "squared_error": sum([(r*r).sum() for r in residuals]),
        }


def get_intervals(cost):
    """Calculate the model selection function given optimal costs.

    For a vector of d real numbers y, Pruned DP gives us a segmented
    vector of d real numbers y^k. The optimal cost of model k is
    c_k=||y-y^k||^2_2 and the input of this function is a list
    c_1,...,c_kmax.

    The model selection function z:R->{1,...,kmax} takes a real number
    L and gives the optimal number of segments for the regularized
    problem where the penalty is the number of segments:
    z(L)=argmin_{k}exp(L)*k+c_k. This function is piecewise constant
    and so we represent it as a list of tuples (k,L_min,L_max) which
    implies that z(L)=k for any L_min < L < L_max.

    """
    max_segments = len(cost)
    cost = numpy.array(cost)
    if numpy.isnan(cost.sum()):
        raise ValueError("cost must not be nan")
    segments = numpy.array(range(max_segments))+1
    i = max_segments-1
    L_min = float('-inf')
    intervals = []
    while i:
        cost_term = cost[i]-cost[:i]
        candidate_segments = segments[:i]
        optimal_segments = segments[i]
        segments_term = candidate_segments-optimal_segments
        intersection = cost_term / segments_term
        first = intersection.argmin()
        L_max = math.log(intersection[first])
        tup = (optimal_segments, L_min, L_max)
        intervals.append(tup)
        i = candidate_segments[first]-1
        L_min = L_max
    intervals.append((1, L_min, float("inf")))
    return tuple(intervals)


def optimal_segments(real_number, intervals):
    """Evaluate a model selection function.

    Model selection functions z(L) are represented as a list of
    intervals of L on which a certain number of segments is
    optimal. This function takes a list of intervals and returns the
    optimal number of segments for a single real number L.

    """
    for segments, m, M in intervals:
        if m < real_number and real_number <= M:
            return segments

# annotation color definitions.


def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i+lv/3], 16) for i in range(0, lv, lv/3))
ANNOTATION_COLORS_HEX = {  # for export to ucsc
    "deletion": "#3564ba",
    "amplification": "#d02a2a",
    "loss": "#93b9ff",
    "normal": '#f6f4bf',
    "gain": "#ff7d7d",
    "1breakpoint": "#ff7d7d",
    "0breakpoints": '#f6f4bf',
    ">0breakpoints": "#a445ee",
    "unlabeled": "#0adb0a",
    "multilabeled": "#000000",
    }
ANNOTATION_COLORS_RGB = {}
ANNOTATION_COLORS_RGB_CSV = {"notImplemented": "0,0,0"}
for k, v in ANNOTATION_COLORS_HEX.iteritems():
    ANNOTATION_COLORS_RGB[k] = tup = hex_to_rgb(v)
    ANNOTATION_COLORS_RGB_CSV[k] = ','.join([str(x) for x in tup])


def add_color(d):
    if "annotation" in d:
        d["color_rgb_csv"] = ANNOTATION_COLORS_RGB_CSV[
            d["annotation"]]


def get_thresh(below, above, dicts):
    """Calculate the best threshold for scores.

    There are n dicts ordered by increasing logratio. Then below and
    above should be arrays of size n-1, corresponding to the n-1
    distinct thresholds at the midpoints between the logratio
    values. The below and above scores should be bigger when the
    threshold is better.

    """
    score = below.cumsum() + above.cumsum()[::-1]
    i = score.argmax()
    # for debugging:
    # print score
    # for j,d in enumerate(dicts):
    #     msg = "thresh after" if i==j else ""
    #     print "%(logratio)10.5f %(annotation)s"%d, msg
    return (dicts[i]["logratio"]+dicts[i+1]["logratio"])/2

COPIES_INTEGER = {
    "deletion": 0,
    "loss": 1,
    "normal": 2,
    "gain": 3,
    "amplification": 4,
    }


def infer_gain_loss(chroms):
    """Assign labels to unlabeled segments.

    Input: a dict[chr]={"segments":[],"breaks":[]}.
    We edit these in-place so nothing needs to be returned.

    """
    labeled = []  # annotations used for training the thresholds.
    to_annotate = []  # annotations which will be assigned gain/normal/loss.
    unique = []
    for seg_info in chroms.values():
        for d in seg_info["segments"]:
            if d["label"] == "unlabeled":
                to_annotate.append(d)
            else:
                ann = d["label"]
                d["annotation"] = ann
                if ann in COPIES_INTEGER:
                    d["copies"] = COPIES_INTEGER[ann]
                    labeled.append(d)
                    if ann not in unique:
                        unique.append(ann)
    # if there are no copy number labels, then everything should be
    # kept unlabeled.
    if len(labeled) == 0:
        for d in to_annotate:
            d["annotation"] = "unlabeled"
        return

    # if there is only 1 copy number annotation, then give every
    # segment that label.
    if len(unique) == 1:
        for d in to_annotate:
            d["annotation"] = unique[0]
        return

    # Otherwise, let's learn some thresholds to predict the copy
    # number of each segment. TDH 29 Mar 2013 Linear time calculation
    # of thresholds. The mis-classification error that we want to
    # minimize over all possible thresholds breaks down into a term
    # below the threshold and a term above the threshold.
    labeled.sort(key=lambda d: d["logratio"])
    copies = numpy.array([d["copies"] for d in labeled])
    below = copies[:-1]
    above = copies[1:][::-1]

    def lower_thresh(copies):
        loss = below < copies
        not_loss = above >= copies
        if loss.any() and not_loss.any():
            return get_thresh(loss, not_loss, labeled)

    def upper_thresh(copies):
        gain = above > copies
        not_gain = below <= copies
        if gain.any() and not_gain.any():
            return get_thresh(not_gain, gain, labeled)

    loss = lower_thresh(2)
    gain = upper_thresh(2)
    amplification = upper_thresh(3)
    deletion = lower_thresh(1)

    for d in to_annotate:
        if amplification is not None and d["logratio"] > amplification:
            d["annotation"] = "amplification"
        elif deletion is not None and d["logratio"] < deletion:
            d["annotation"] = "deletion"
        elif loss is not None and d["logratio"] < loss:
            d["annotation"] = "loss"
        elif gain is not None and d["logratio"] > gain:
            d["annotation"] = "gain"
        else:
            d["annotation"] = "normal"
    return
    for d in dicts:  # TODO: do this for bed export.
        add_color(d)

COPIES_EXPORT_URL = """
http://bioviz.rocq.inria.fr/export/%(user)s/%(name)s/copies/bed/
"""

PROFILE_EXPORT_URLS = """
http://bioviz.rocq.inria.fr/secret/%(name)s.bedGraph.gz
http://bioviz.rocq.inria.fr/export/%(user)s/%(name)s/regions/bed/
http://bioviz.rocq.inria.fr/export/%(user)s/%(name)s/segments/bedGraph/
http://bioviz.rocq.inria.fr/export/%(user)s/%(name)s/breaks/bed/
http://bioviz.rocq.inria.fr/export/%(user)s/%(name)s/copies/bed/
"""

def reprocess_all_profiles():
    for pname in Profile.db_keys():
        pro=Profile(pname)
        d = pro.get()
        d["ready"]=False
        pro.put(d)
    print "all profiles set to ready=False"

def all_profiles_ready():
    for pname in Profile.db_keys():
        pro=Profile(pname)
        d = pro.get()
        d["ready"]=True
        pro.put(d)
    print "all profiles set to ready=True"
    while db.ProfileQueue.db.consume():
        pass
    print "ProfileQueue is empty"

class Profile(Resource):
    keys = ("name", )
    RELATED = ("Breakpoints", "Copies", "Profile", "Models",
        "AnnotationCounts", "DisplayedProfile",
        "ChromProbes", "ModelError",
        )

    def delete(self):
        """Delete all info for this profile.

        Return a message to the admin user about what was deleted, or
        raise an exception if for some reason it could not be deleted.

        """
        deleted = []
        pro_info = self.get()
        pro_name = pro_info["name"]
        for db_key in UserProfiles.db_keys():
            up = UserProfiles(db_key)
            up.remove(pro_name)
        # To delete:
        for cls_name in self.RELATED:
            cls = eval(cls_name)
            keys = cls.db_keys()
            for key_txt in keys:
                values = key_txt.split(" ")
                key_dict = dict(zip(cls.keys, values))
                if key_dict["name"] == pro_name:
                    res = cls(*values)
                    deleted.append(str(res))
                    res.put(None)
        # TODO: make file deletion cross-platform.
        name = self.values[0]
        cmd = "rm -rf %s/%s" % (SECRET_DIR, name)
        os.system(cmd)
        deleted.append("files")
        return "deleted " + ", ".join(deleted)

    def get_export(self, user):
        p = self.get()
        d = {"name": self.values[0], "user": user}
        p["ucsc"] = PROFILE_EXPORT_URLS % d
        p["user"] = user
        return p

    def regions(self, user):
        dicts = []
        name = self.values[0]
        for ch in ChromLengths.CHROM_ORDER:
            for short, table in REGION_TABLES:
                for d in table(user, name, ch).json():
                    d["type"] = short
                    d["chromosome"] = ch
                    add_color(d)
                    dicts.append(d)
        return dicts

    def breaks(self, user):
        return self.displayed("breakpoints", user, annotation="1breakpoint")

    def segments(self, user):
        return self.displayed("segments", user)

    def copies(self, user, color=False):
        return self.displayed("segments", user)

    def displayed(self, what, user, color=True, **kwargs):
        dicts = []
        name = self.values[0]
        chroms = DisplayedProfile(user, name).get()
        for ch, model in chroms.iteritems():
            for d in model[what]:
                d["chromosome"] = ch
                d.update(kwargs)
                if color:
                    add_color(d)
                dicts.append(d)
        return dicts

    def process(self):
        """L2-optimal segmentations and model selection functions.

        As soon as profiles are uploaded to the server, it responds
        and tells the user that processing has begun. In fact, each
        new profile enters the ProfileQueue, and a daemon process will
        run this method on 1 profile at a time.

        We use the PrunedDP module to calculate the L2-optimal
        segmentation for several model sizes k=1,...,Kmax, then
        calculate a piecewise constant model selection function z(L)
        which maps penalty values (real numbers L) to model sizes
        (1,...,Kmax).

        On completion, we set ready to True.

        """
        #before = time.time()
        pinfo = self.get()
        # print "pinfo- ", pinfo
        if pinfo is None:
            # This profile was deleted before processing!
            return
        bases = ChromLengths(pinfo["db"]).get()
        total_bases = sum(bases.values())
        # print "bases- ", bases
        # print "total_bases- ", total_bases

        for ch in pinfo["chrom_meta"]:
            probes = ChromProbes(pinfo["name"], ch).get()
            # print "ChromProbes: ", probes
            kmax = min(len(probes["logratio"]), pinfo["maxSegments"])
            segmat = PrunedDP(probes["logratio"], kmax)
            models = [
                get_model(probes, segmat[k, :k])
                for k in range(kmax)
                ]
            sq_err = [m["squared_error"] for m in models]
            r = Models(pinfo["name"], ch)
            r.put(models)
            # TODO: this profile may have some annotated regions! If
            # so, we should delete them, delete ModelError (which has
            # dimension which depends on the maximum number of
            # segments) then add the annotated regions back.
            meta = pinfo["chrom_meta"][ch]
            meta["intervals"] = get_intervals(sq_err)
            diffs = numpy.diff(probes["logratio"])
            features = [
                math.log(numpy.median(numpy.abs(diffs))),
                math.log(len(probes["logratio"])),
                ]
            meta["features"] = numpy.array(features)
            # make scatter plots.
            zoom5_px = meta["probes"]*5
            if zoom5_px > CHROME_UBUNTU_MAX:
                zoom5_px = CHROME_UBUNTU_MAX
            zoom20_px = meta["probes"]*20
            if zoom20_px > CHROME_UBUNTU_MAX:
                zoom20_px = CHROME_UBUNTU_MAX
            small_px = int(float(bases[ch])/total_bases * DEFAULT_WIDTH)
            # print "meta- %s\n" %meta
            plot_info = (
                ("profiles", -1, 1, small_px),
                ("profile", pinfo["logratio_min"], pinfo["logratio_max"],
                 small_px),
                ("standard", meta["logratio_min"], meta["logratio_max"],
                 DEFAULT_WIDTH),
                ("ipad", meta["logratio_min"], meta["logratio_max"], IPAD_MAX),
                ("chrome_windows",
                 meta["logratio_min"], meta["logratio_max"],
                 CHROME_WINDOWS_MAX),
                ("chrome_ubuntu",
                 meta["logratio_min"], meta["logratio_max"],
                 CHROME_UBUNTU_MAX),
                #("1pixel_per_probe",meta["logratio_min"],meta["logratio_max"],
                # zoom2_px),
                # ("5pixels_per_probe",
                #  meta["logratio_min"], meta["logratio_max"],
                #  zoom5_px),
                # ("20pixels_per_probe",meta["logratio_min"],
                #  meta["logratio_max"],zoom20_px),
                )
            meta["plots"] = {}
            for name, lr_min, lr_max, width in plot_info:
                meta["plots"][name] = {
                    "logratio_min": lr_min,
                    "logratio_max": lr_max,
                    "height_px": HEIGHT_PX,
                    "width_px": width,
                    "width_bases": bases[ch],
                    "file": scatterplot_file(pinfo["name"], ch, name,
                                             lr_min, lr_max,
                                             width, bases),
                    }
                #print "file created: ", meta["plots"][name]["file"]
                #print "---------------"
                #if meta["plots"][name]["width_px"] > DEFAULT_WIDTH :
                #split_image(meta["plots"][name]["file"], ch, pinfo["name"], name, width)
            # print "meta- ",meta
            # print "\n\n\n\n----------\n\n\n\n\n"
        print "%s ready"%pinfo["name"]
        pinfo["ready"] = True
        print pinfo
        self.put(pinfo)
        # print time.time()-before, "seconds elapsed"


class Models(Resource):
    keys = ("name", "chr")


class Breakpoints(Regions):
    keys = ("user", "name", "chrom")
    pass


class Copies(Regions):
    keys = ("user", "name", "chrom")
    pass

REGION_TABLES = (
    ("breakpoints", Breakpoints),
    ("copies", Copies),
    )
REGION_TABLES_DICT = dict([
    (short, table)
    for short, table in REGION_TABLES
    ])


class AnnotationCounts(Resource):
    keys = ("user", "name")

    def make_details(self):
        table_count = {}
        for short, table in REGION_TABLES:
            table_count[short] = {}
            for ch in ChromLengths.CHROM_ORDER:
                r = table(self.info["user"], self.info["name"], ch)
                table_count[short][ch] = r.count()
        counts = {}
        for ch in ChromLengths.CHROM_ORDER:
            counts[ch] = table_count["breakpoints"][ch]
        for short, d in table_count.iteritems():
            counts[short] = 0
            for ch in ChromLengths.CHROM_ORDER:
                counts[short] += table_count[short][ch]
        return counts


class UserModel(Resource):
    keys = ("user",)

    def make_details(self):
        # defaults from the ICML 2013 paper.
        return (-2.0, numpy.array([1.3, 0.93]))

    def predict(self, features):
        if not hasattr(self, "coef"):
            self.coef = self.get()  # cache
        intercept, weights = self.coef
        return intercept + (weights*features).sum()

    def learn(self):
        """Update the weights and intercept based on annotations.

        Called by the daemon.

        """
        #txn = env.txn_begin()
        user = self.values[0]
        uerr = UserError(user)
        #err_dict = uerr.get(txn)
        err_dict = uerr.get()
        if len(err_dict) == 0:
            # txn.commit()
            # print "%s: nothing to learn."%self.values
            return
        # get features for new signals.
        uerr.put({})
        # txn.commit()
        profiles = {}
        for k in err_dict.keys():
            pro, ch = k
            ptups = profiles.setdefault(pro, [])
            ptups.append((ch, err_dict[k]))
        ts = TrainingSet(user)
        train = ts.get()
        # analyze the error curves to get a target interval.
        for pro, tups in profiles.iteritems():
            pinfo = Profile(pro).get()
            for ch, err in tups:
                meta = pinfo["chrom_meta"][ch]
                features = meta["features"]
                tint = target_interval(err, meta["intervals"])
                if tint == (float("-inf"), float("inf")):
                    if (pro, ch) in train:
                        train.pop((pro, ch))
                else:
                    train[(pro, ch)] = (features, tint)
        ts.put(train)
        # Don't even try to learn unless there is at least 2 training
        # examples.
        if len(train) <= 1:
            return
        # Convert to arrays for optimization.
        X = []
        L = []
        for features, tint in train.values():
            X.append(features)
            L.append(tint)
        X = numpy.array(X)
        L = numpy.array(L)
        #X.tofile("X.csv",sep=" ")
        #L.tofile("L.csv",sep=" ")
        # print L
        # gradient descent learning.
        param_before = self.get()  # warm restart.
        params = mmir(X, L, param_before)
        for p in params:
            if not numpy.isfinite(p).all():
                return
        # print param_before, "before"
        # print params, "after"
        self.put(params)


def target_interval(err, intervals):
    """Do a linear scan of the penalized model error function to
    determine the target interval."""
    eint = [(err[k-1], m, M) for k, m, M in intervals]
    last_e, last_m, last_M = eint[len(eint)-1]
    # fake interval that will always break, so the code below is
    # clearer and less repetitive.
    eint.append((float("inf"), last_M, None))
    best = None
    best_size = 0
    best_err = float("inf")
    e, m, M = eint[0]
    left_e = e
    left_penalty = m
    right_i = 1
    while right_i < len(eint):
        e, m, M = eint[right_i]
        if e != left_e:  # a break in the error curve.
            size = m-left_penalty
            better_error = left_e < best_err
            better_size = (left_e == best_err) and (size > best_size)
            if better_error or better_size:
                # this is the best interval so far.
                best_size = size
                best_err = left_e
                biggest = (left_penalty, m)
            left_e = e
            left_penalty = m
        right_i += 1
    return biggest


class TrainingSet(Resource):
    keys = ("user", )

    def make_details(self):
        return {}


def chrom_model(models, error, regions, profile, ch, user,
                chrom_meta=None, user_model=None):
    """Calculate a model that is consistent with regions.

    Used for add/remove breakpoint region and initial DisplayedProfile."""
    optimal_err = error.min()
    if optimal_err == 0:
        is_min = (error == 0).nonzero()[0]
        if len(is_min) == 1:
            model_index = is_min[0]
        else:
            # use learned model to disambiguate.
            if user_model is None:
                user_model = UserModel(user)
            if chrom_meta is None:
                p = Profile(profile).get()
                chrom_meta = p["chrom_meta"][ch]
            penalty_value = user_model.predict(chrom_meta["features"])
            segments = optimal_segments(
                penalty_value, chrom_meta["intervals"])
            target_index = segments-1
            dist_to_target = numpy.abs(is_min - target_index)
            model_index = is_min[dist_to_target.argmin()]
        model = models[model_index]["json"]
    else:
        # run SegAnnot to get a consistent segmentation.
        probes = ChromProbes(profile, ch).get()
        break_anns = [
            b for b in regions["data"].values()
            if b["annotation"] == "1breakpoint"
            ]
        break_anns.sort(key=lambda b: b["min"])
        min_array = numpy.array([b["min"] for b in break_anns],
                                numpy.int32)
        max_array = numpy.array([b["max"] for b in break_anns],
                                numpy.int32)
        result = SegAnnotBases(probes["logratio"],
                               probes["chromStart"],
                               min_array,
                               max_array)
        model = {
            "segments": tuple([
                {"min": int(start), "max": int(end), "logratio": float(mu)}
                for start, end, mu
                in zip(result["start"], result["end"], result["mean"])
                ]),
            "breakpoints": tuple([
                {"min": int(m), "position": int(p), "max": int(M)}
                for m, p, M in
                zip(result["break_min"],
                    result["break_mid"], result["break_max"])
                ]),
            "segannot": True,
            }
    # label segments using copy number annotations.
    copies = Copies(user, profile, ch).json()
    copies.sort(key=lambda d: d["mid"])
    segments = []
    for segment in model["segments"]:
        segment["label"] = "unlabeled"
        segment["copies"] = {}
        while copies and copies[0]["mid"] < segment["max"]:
            copy = copies.pop(0)
            ann = copy["annotation"]
            segment["copies"][copy["id"]] = ann
            label_segment(ann, segment)
        segments.append(segment)
    model["segments"] = segments
    return model


class DisplayedProfile(Resource):

    """All the current segments and copy number predictions."""
    keys = ("user", "name")

    def add(self, region, ch):
        self.region = region
        self.ch = ch
        return self.alter(self.add_region)

    def remove(self, region, ch):
        self.region = region
        self.ch = ch
        return self.alter(self.remove_region)

    def add_region(self, chroms):
        model = chroms[self.ch]
        add_copy_region(self.region, model)
        infer_gain_loss(chroms)
        return chroms

    def remove_region(self, chroms):
        model = chroms[self.ch]
        segment = region_in_segment(self.region, model["segments"])
        segment["label"] = "unlabeled"
        region_dict = segment.setdefault("regions", {})
        if self.region["id"] in region_dict:
            region_dict.pop(self.region["id"])
            for ann in region_dict.values():
                label_segment(ann, segment)
            infer_gain_loss(chroms)
        else:  # this should only be when the db is out of sync.
            chroms = self.make_details()
        return chroms

    def make_details(self):
        """Called on a previously unseen profile."""
        p = Profile(self.info["name"]).get()
        chrom_meta = p["chrom_meta"]
        chroms = {}
        user_model = UserModel(self.info["user"])
        for ch, meta in chrom_meta.iteritems():
            error = ModelError(self.info["user"], self.info["name"], ch).get()
            brks = Breakpoints(self.info["user"], self.info["name"], ch).get()
            models = Models(self.info["name"], ch).get()
            model = chrom_model(models, error, brks,
                                self.info["name"], ch, self.info["user"],
                                meta, user_model)
            copies = Copies(self.info["user"], self.info["name"], ch).json()
            for region in copies:
                add_copy_region(region, model)
            chroms[ch] = model
        infer_gain_loss(chroms)
        return chroms


def add_copy_region(region, model):
    segment = region_in_segment(region, model["segments"])
    ann = region["annotation"]
    region_dict = segment.setdefault("regions", {})
    region_dict[region["id"]] = ann
    label_segment(ann, segment)


def region_in_segment(region, segments):
    for segment in segments:
        if region["mid"] < segment["max"]:
            return segment


def label_segment(ann, segment):
    if segment["label"] == "unlabeled":
        segment["label"] = ann
    elif segment["label"] != ann:
        segment["label"] = "multilabeled"


class ProfileQueue(Resource):
    DBTYPE = bsddb3.db.DB_QUEUE
    RE_LEN = 50

    keys = ("name", )

    @classmethod
    def process_one(cls):
        stat_dict = cls.db.stat()
        if stat_dict["nkeys"] == 0:  # empty queue
            profiles = Profile.all()
            # profiles whose names are for some reason missing from the queue
            not_ready = [p for p in profiles if not p["ready"]]
            for p in not_ready:
                cls.db.append(p["name"])
        recid, name = cls.db.consume_wait()
        pro = Profile(name.strip())  # need to remove queue padding.
        pro.process()

class ChromProbes(Resource):
    keys = ("name", "chrom")


class UserProfiles(ResList):

    """List of available profiles for each user."""
    keys = ("user", )

    def make_details(self):
        profiles = Profile.all()
        return [p["name"] for p in profiles if self.compatible(p)]

    def compatible(self, pinfo):
        """Decide if a profile can be viewed by this user."""
        u = self.values[0]
        criteria = [
            pinfo["uploader"] == u,
            pinfo["share"] == "public",
            u and u.endswith(pinfo["share"]),
            ]
        return any(criteria)


class Vector(Container):

    def add_item(self, V):
        return V + self.item

    def remove_item(self, V):
        self.removed = self.item
        return V - self.item


class ModelError(Vector):
    keys = ("user", "name", "chr")

    def make_details(self):
        models = Models(self.info["name"], self.info["chr"]).get()
        error = numpy.array([0 for m in models])
        return error
