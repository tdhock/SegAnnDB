from pyramid.view import view_config
from pyramid.exceptions import Forbidden
from pyramid.httpexceptions import HTTPFound
# from pyramid.security import authenticated_userid
from pyramid.response import FileResponse, Response
from random import shuffle
import pdb
import gzip
import numpy
import db
import os
from datetime import datetime
import json

# I am trying to override the authenticated_userid function here
# retrieve the cookie and return to the user
def authenticated_userid(request):
    """This function returns the user_id from the request"""
    try:
        val = request.cookies["authtkt"]
    except:
        # in case the cookie is not found it applies, unauthenticated user
        val = None;
    return val

def add_userid(fn):
    def view(request):
        d = fn(request)
        d["user"] = authenticated_userid(request)
        return d
    return view


def not_anonymous(fn):
    """Raise Forbidden if user is not logged in."""
    def view(request):
        userid = authenticated_userid(request)
        if userid is None:
            raise Forbidden()
        return fn(request)
    return view


def forbidden_userprofiles(request):
    userid = authenticated_userid(request)
    allowed = db.UserProfiles(userid).get()
    md = request.matchdict
    looking = md["profiles"].split(',') if "profiles" in md else []
    if "name" in md:
        for name in md["name"].split(","):
            looking.append(name)
    # print looking, allowed
    for pname in looking:
        if pname not in allowed:
            raise Forbidden()


def check_userprofiles(fn):
    """Raise Forbidden if user shouldn't access profile."""
    def view(request):
        forbidden_userprofiles(request)
        return fn(request)
    return view


def check_export(fn):
    """Raise Forbidden if this profile can't be exported."""
    def view(request):
        names = request.matchdict["name"].split(",")
        for name in names:
            pinfo = db.Profile(name).get()
            if pinfo is None or pinfo["export"] == "no":
                return forbidden_userprofiles(request)
        return fn(request)
    return view

ADMIN_USERS = ["tdhock5@gmail.com", "x.abhishek.flyhigh@gmail.com"]


def admin_only(fn):
    """Raise Forbidden if user is not on the admin list."""
    def view(request):
        userid = authenticated_userid(request)
        if userid not in ADMIN_USERS:
            raise Forbidden("not admin user")
        return fn(request)
    return view


@view_config(route_name="delete_profile")
def delete_profile(request):
    userid = authenticated_userid(request)
    profile = db.Profile(request.matchdict["name"])
    profile_info = profile.get()
    if profile_info["uploader"] != userid:
        raise Forbidden("profile can only be deleted by uploader")
    try:
        pro_msg = profile.delete()
    except Exception, e:
        pro_msg = "ERROR: " + str(e)
    response = Response(content_type="text/plain")
    response.write(pro_msg)
    return response


@view_config(route_name="secret")
@check_export
def secret(request):
    fn = db.secret_file("%(name)s%(suffix)s" % request.matchdict)
    return FileResponse(fn, request=request)


@view_config(route_name="secret_new")
def secret_new(request):
    """
    New secret view for the new chromosome viewer.

    This is most probably used for uploading the new images ?
    """
    # fn = db.secret_file("%(name)s%(suffix)s" % request.matchdict)
    # return FileResponse(fn, request=request)
    profileName = request.matchdict["profile_name"]
    chr_num = request.matchdict["chr_num"]
    file_name = "%(name)s%(suffix)s" % request.matchdict
    fn = db.secret_file(file_name, chr_num)
    return FileResponse(fn, request=request)


def table_profiles(names, userid):
    profiles = []
    for pname in names:
        p = db.Profile(pname).get_export(userid)
        # add info for how many annotations for this user.
        counts = db.AnnotationCounts(userid, pname).get()
        p.update(counts)
        profiles.append(p)
    return profiles


@view_config(route_name='home', renderer='templates/home.pt')
def home(request):
    userid = authenticated_userid(request)
    profile_names = db.UserProfiles(userid).get()
    # show only a few of the most recently uploaded profiles.
    profiles = table_profiles(profile_names[:5], userid)
    info = {
        'profile_count': len(profile_names),
        'profiles': profiles,
        'user': userid,
    }
    pname = 'nb18'
    if pname in profile_names:
        info['plot'] = plotJS([pname], ['17'], 'standard')
    else:
        info["plot"] = None
    return info


@view_config(route_name="upload",
             request_method="GET",
             renderer="templates/upload.pt")
@not_anonymous
@add_userid
def display_upload(request):
    return {}


def read_header(line):
    """Parse and check probe header.

    Raises ValueError if there was a problem.

    """
    results = {}
    # check for several things in the header.
    line = line.replace("\n", " ")
    for var, (pattern, regex) in db.HEADER_REGEXES.iteritems():
        match = regex.search(line)
        if not match:
            raise ValueError("header does not indicate '%s'" % pattern)
        results[var] = match.groups()[0]
    MAX = 30
    if len(results["name"]) > MAX:
        raise ValueError("profile names must be %d characters or less" % MAX)
    if results["share"] == "public" and results["export"] == "no":
        raise ValueError("share=public implies export=yes")
    results["maxSegments"] = int(results["maxSegments"])
    return results


def check_max(pos, txt, ch, chrom_lengths):
    """Raise ValueError if pos > chrom_lengths[ch]."""
    if ch in chrom_lengths:
        max_bases = chrom_lengths[ch]
        if int(pos) > max_bases:
            raise ValueError(
                "%s=%s > max(chr%s)=%s" % (
                    txt, pos, ch, max_bases))


def read_probes(lines, chrom_lengths):
    """Parse and check probe lines.

    Raises ValueError if there was a problem.

    """
    # check each line for the correct format.
    chroms = {}
    for line in lines:
        match = db.LINE_REGEX.match(line.strip())
        if not match:
            raise ValueError("line\n%sdoes not match '%s'" % (
                line, db.LINE_PATTERN))
        ch, chromStart, chromEnd, logratio = match.groups()
        check_max(chromStart, "chromStart", ch, chrom_lengths)
        check_max(chromEnd, "chromEnd", ch, chrom_lengths)
        tup = (int(chromStart), float(logratio))
        probeList = chroms.setdefault(ch, [])
        probeList.append(tup)
    # only store data for chrom for which we have the length, if there
    # are at least 2 probes.
    chrom_meta = {}
    for ch in chroms.keys():
        if ch not in chrom_lengths:
            raise ValueError(
                ch + " not in possible chroms: " +
                ",".join(chrom_lengths.keys()))
        probeList = chroms.pop(ch)
        if len(probeList) > 1:
            probeList.sort(key=lambda tup: tup[0])  # position, logratio
            chromStart = numpy.array([
                pos for pos, lr in probeList], numpy.int32)
            chroms[ch] = {
                "logratio": numpy.array([
                    lr for pos, lr in probeList], numpy.float),
                "chromStart": chromStart,
                }
            ch_lr = chroms[ch]["logratio"]
            chrom_meta[ch] = {
                "logratio_min": min(ch_lr),
                "logratio_max": max(ch_lr),
                "probes": len(ch_lr),
                }
    return {
        "logratio_min": min([d["logratio_min"] for d in chrom_meta.values()]),
        "logratio_max": max([d["logratio_max"] for d in chrom_meta.values()]),
        "probes": sum([d["probes"] for d in chrom_meta.values()]),
        "chroms": chroms,
        "chrom_meta": chrom_meta,
        }

TARGET_BREAKS = {
    "0breakpoints": 0,
    "1breakpoint": 1,
    }


@view_config(route_name="add_region",
             renderer="json")
@check_userprofiles
def add_region(request):
    md = request.matchdict
    userid = authenticated_userid(request)
    table = db.REGION_TABLES_DICT[md["trackType"]]
    regions = table(userid, md["name"], md["chr"])
    # TODO: check if the region that we add has the same min value as
    # an existing annotation. In that case the SegAnnot segmentation
    # is undefined and so we should reject the new annotation.
    db.AnnotationCounts(userid, md["name"]).put(None)
    reg = {
        "min": int(md["min"]),
        "max": int(md["max"]),
        "annotation": md["annotation"],
        }
    # first calculate error of this region.
    if md["trackType"] == "breakpoints":
        models = db.Models(md["name"], md["chr"]).get()
        breaks = numpy.array([
            ((reg["min"] < m["breaks"]) & (m["breaks"] < reg["max"])).sum()
            for m in models
            ])
        error = breaks != TARGET_BREAKS[reg["annotation"]]
        reg["error"] = error.astype(int)
    added, after = regions.add(reg)
    # then add to the total error.
    result = {}
    if md["trackType"] == "breakpoints":
        evec = db.ModelError(userid, md["name"], md["chr"])
        err_added, err_after = evec.add(reg["error"])
        chroms = update_model(models,
                              err_after,
                              after,
                              md["name"],
                              md["chr"],
                              userid)
    else:
        res = db.DisplayedProfile(userid, md["name"])
        chroms = res.add(added, md["chr"])
    # do not send numpy error.
    if "error" in added:
        added.pop("error")
    result["updates"] = [{
        "profile_id": md["name"],
        "chromosome": ch,
        "update": model,
        } for ch, model in chroms.iteritems()]
    result["region"] = added
    return result


@view_config(route_name="delete_region",
             renderer="json")
@check_userprofiles
def delete_region(request):
    md = request.matchdict
    userid = authenticated_userid(request)
    table = db.REGION_TABLES_DICT[md["trackType"]]
    db.AnnotationCounts(userid, md["name"]).put(None)
    regions = table(userid, md["name"], md["chr"])
    removed, after = regions.remove(int(request.matchdict["id"]))
    result = {}
    if md["trackType"] == "breakpoints":
        evec = db.ModelError(userid, md["name"], md["chr"])
        err_removed, err_after = evec.remove(removed["error"])
        chroms = update_model(db.Models(md["name"], md["chr"]).get(),
                              err_after,
                              after,
                              md["name"],
                              md["chr"],
                              userid)
    else:
        res = db.DisplayedProfile(userid, md["name"])
        chroms = res.remove(removed, md["chr"])
    result["updates"] = [{
        "profile_id": md["name"],
        "chromosome": ch,
        "update": model,
        } for ch, model in chroms.iteritems()]
    return result


def update_model(models, error, regions, profile, ch, user):
    """Used in add/remove breakpoint regions."""
    # store error for learning later.
    uerr = db.UserError(user)
    uerr.add((profile, ch, error))
    model = db.chrom_model(models, error, regions, profile, ch, user)
    res = db.DisplayedProfile(user, profile)
    chroms = res.get()
    chroms[ch] = model
    db.infer_gain_loss(chroms)
    res.put(chroms)
    return chroms


@view_config(route_name="profile",
             renderer="templates/plot_profile.pt")
@add_userid
@check_userprofiles
def profile(request):
    return prof_info(
        request.matchdict["name"],
        None,
        "profile")


def prof_info(name_str, chroms, size):
    """
    Parameters -
    name-str - name of profile
    chroms - number of chromosomes
    size - zoom level

    Returns -
    a dict containing the profile data
    """
    out = {"names": name_str}
    if "," in name_str:
        namelist = name_str.split(",")
        p = None
        out["p"] = None
    else:
        namelist = [name_str]
        p = db.Profile(name_str).get()
        out["p"] = p
    if chroms == None:
        if p is None:
            p = db.Profile(namelist[0]).get()
        cl = db.ChromLengths(p["db"])
        cl_info = cl.get()
        chroms = cl_info.keys()
    out["plot"] = plotJS(namelist, chroms, size)
    return out


@view_config(route_name="view_profiles")
def view_profiles(request):
    profiles = request.POST.getall("profile")
    prof_str = ",".join(profiles)
    return HTTPFound("/profile/%s/" % prof_str)


@view_config(route_name="about", renderer="templates/about.pt")
@add_userid
def about(request):
    return {}

CHROM_ZOOMS = ("standard", "ipad", "chrome_windows", "chrome_ubuntu")

"""
This is the older chrom method.
TODO: Need to rework it so that old chrom viewer works as well
"""
@view_config(route_name="old_chrom",
             renderer="templates/plot_chrom.pt")
@add_userid
@check_userprofiles
def old_chrom(request):
    w = request.GET.get("width", "standard")
    md = request.matchdict
    out = prof_info(md["name"], md["chr"].split(','), w)
    out["name"] = md["name"]
    out["width"] = w
    out["others"] = [z for z in CHROM_ZOOMS if z != w]
    out["chr"] = md["chr"]
    return out

@view_config(route_name='new_chrom', renderer='templates/new.pt')
@add_userid
@check_userprofiles
def new_chrom(request):
    """
    TODO: Add more documentation about this method.
    Related to the new chrom viewer
    """
    w = request.GET.get("width", "standard")
    i = request.GET.get("index", "")
    md = request.matchdict
    out = prof_info(md["name"], md["chr"].split(','), w)
    out["name"] = md["name"]
    out["width"] = w
    out["others"] = [z for z in CHROM_ZOOMS if z != w]
    out["chr"] = md["chr"]

    # in case of standard width we want to send the correct suffixes
    #
    # index = index of the image we are going to show. No index will output the
    #         full image for that zoom level.
    #
    # index_next = the next index , right after the current index
    # index_prev = the prev index, right before the curernt index
    # index_suffix = used to generate the image file name in the js code

    if w == "standard":
        out["index"] = 0
        out["index_next"] = ""
        out["index_prev"] = ""
        out["index_suffix"] = ""
    else:
        out["index"] = i
        out["index_suffix"] = "_" + i

        if i == "":
            # means, we want to view the full zoom level
            out["index_next"] = "1"
            out["index_prev"] = ""
            out["index_suffix"] = ""
        elif int(i) == 1:
            out["index_next"] = str(int(i)+1)
            out["index_prev"] = "1"
        else:
            out["index_next"] = str(int(i)+1)
            out["index_prev"] = str(int(i)-1)

    return out


@view_config(renderer="json",
             route_name="initial")
@check_userprofiles
def initial(request):
    """Send user-specific model data as JSON."""
    userid = authenticated_userid(request)
    result_list = []
    for name in request.matchdict["profiles"].split(","):
        dp = db.DisplayedProfile(userid, name)
        # dp.put(None)
        prof = dp.get()
        for ch in request.matchdict["chromosomes"].split(","):
            if ch in prof:
                m = prof[ch]  # contains breaks, copy number calls.
                m["breakpoints_regions"] = db.Breakpoints(
                    userid, name, ch).json()
                for b in m["breakpoints_regions"]:
                    # do not send numpy error.
                    b.pop("error")
                m["copies_regions"] = db.Copies(userid, name, ch).json()
                result_list.append({
                    "chromosome": ch,
                    "profile_id": name,
                    "update": m,
                    })
    return {
        "updates": result_list,
        }


def plotJS(profiles, chroms, size):
    """JSON to pass to profilePlot JS code.

    A list of list of objects. The first list corresponds to
    rows/profiles in the plot table, the second list corresponds to
    columns/chroms.

    """
    # TODO: when we have multiple genomes, check to make sure we are
    # only displaying profiles from one!
    pinfo = []
    for name in profiles:
        pro = db.Profile(name).get()
        meta = pro["chrom_meta"]
        cinfo = []
        for ch in chroms:
            d = meta[ch]["plots"][size] if ch in meta else {}
            d["profile"] = name
            d["chr"] = ch
            d["db"] = pro["db"]
            cinfo.append(d)
        pinfo.append(cinfo)
    return json.dumps(pinfo)


@view_config(route_name="csv_profiles")
def csv_profiles(request):
    info = all_profiles(request)
    resp = respond_bed_csv("profiles", "csv", {}, info["profiles"])
    return resp


@view_config(route_name="all_profiles",
             renderer="templates/all_profiles.pt")
def all_profiles(request):
    userid = authenticated_userid(request)
    profile_names = db.UserProfiles(userid).get()
    profiles = table_profiles(profile_names, userid)
    urls = [db.COPIES_EXPORT_URL % p for p in profiles if p["copies"] > 0]
    info = {
        'profile_count': len(profile_names),
        "copy_urls": "\n".join(urls),
        'profiles': profiles,
        'user': userid,
        }
    return info


def unannotated(userid):
    """Find an un-annotated chromosome."""
    names = db.UserProfiles(userid).get()
    shuffle(names)
    chorder = list(db.ChromLengths.CHROM_ORDER)
    shuffle(chorder)
    for name in names:
        ac = db.AnnotationCounts(userid, name)
        counts = ac.get()
        for ch in chorder:
            if counts[ch] == 0:
                return name, ch


@view_config(route_name="random")
def random(request):
    userid = authenticated_userid(request)
    name, ch = unannotated(userid)
    return HTTPFound("/profile/%s/%s/" % (name, ch))


@view_config(route_name="upload",
             request_method="POST",
             renderer="templates/upload_profile.pt")
@add_userid
def upload_profile(request):
    try:
        upload = request.POST["file"].file
    except AttributeError:
        return {"error": "no file selected"}
    try:
        userid = request.POST["user"]
    except AttributeError:
        return {"error": "no user specified"}
    return upload_profile_user_file(userid, upload)


def upload_profile_user_file(userid, upload):
    """Separate from upload_profile for testing."""
    db_users = db.UserProfiles.db_keys()
    if userid not in db_users:
        return {"error": "unknown user "+userid}
    # need to specify mode r since upload is in wb mode, and GzipFile
    # inherits that mode by default.
    try:
        f = gzip.GzipFile(fileobj=upload, mode="r")
        header = f.readline()
    except IOError:
        f = upload
        header = f.readline()
    try:
        info = read_header(header)
        hg = info["db"]
        cl = db.ChromLengths(hg).get()
        # reject if we have no chrom info for this genome.
        if cl is None:
            return {"error": "unsupported genome %s" % hg}
        # reject if another profile has the same name.
        if db.Profile.has_key(info["name"]):
            return {"error": "profile named '%(name)s' already in db" % info}
        probeInfo = read_probes(f, cl)
    except ValueError, e:
        return {"error": e}
    chroms = probeInfo.pop("chroms")
    for cname, probes in chroms.iteritems():
        # the regexp that we use for validating the logratio column is
        # quite permissive: \S+ so it can match 213E-2 and also NaN,
        # thus we need to check to make sure there are no NaN
        # logratios, and stop with an error if there are.
        nan_probes = numpy.isnan(probes["logratio"]).sum()
        if 0 < nan_probes:
            return {"error": "%d nan probes on chr%s" % (nan_probes, cname)}
        r = db.ChromProbes(info["name"], cname)
        r.put(probes)
    r = db.Profile(info["name"])
    info.update(probeInfo)
    info["uploader"] = userid
    info["uploaded_on"] = datetime.now()
    info["ready"] = False
    r.put(info)
    # save gz profile to disk.
    f.seek(0)
    out_name = db.secret_file("%(name)s.bedGraph.gz" % info)
    saved = gzip.open(out_name, "w")
    for data in f:
        saved.write(data)
    saved.close()
    # add profile to user lists.
    uprofs = [db.UserProfiles(u) for u in db_users]
    to_update = [r for r in uprofs if r.compatible(info)]
    for r in to_update:
        r.add(info["name"])
    # add profile to processing queue.
    db.ProfileQueue.db.append(info["name"])
    # need to return error none to avoid template nameError.
    info["error"] = None
    return info

HEADER_TEMPLATES = {
    "bed": 'track visibility=%(visibility)s name=%(name)s%(table)s description="%(description)s %(table)s" itemRgb=on',
    "bedGraph": 'track type=bedGraph visibility=%(visibility)s alwaysZero=on graphType=points yLineMark=0 yLineOnOff=on name=%(name)s%(table)s description="%(description)s %(table)s"',
    }
CSV_EXPORT_FORMATS = {
    "regions": (
        "user_id",
        "profile_id",
        "chromosome",
        "min",
        "max",
        "type",
        "annotation",
        ),
    "copies": (
        "profile_id",
        "chromosome",
        "min",
        "max",
        "logratio",
        "annotation",
        ),
    "breaks": (
        "profile_id",
        "chromosome",
        "min",
        "position",
        "max",
        ),
    "profiles": (
        "name",
        "db",
        "copies",
        "breakpoints",
        "probes",
        "uploader",
        "uploaded_on",
        "share",
        "export",
        "description",
        ),
    }
MODEL_FORMATS = (
    ("bed", ("regions", "copies", "breaks"), ' '.join([
        "chr%(chromosome)s",
        "%(min)s",
        "%(max)s",
        "%(annotation)s",
        "0",
        ".",
        "%(min)s",
        "%(max)s",
        "%(color_rgb_csv)s",
        ])),
    ("bedGraph", ("segments",), ' '.join([
        "chr%(chromosome)s",
        "%(min)s",
        "%(max)s",
        "%(logratio)s",
        ])),
    )
EXPORT_FORMATS = {}
for file_type, tables, fmt in MODEL_FORMATS:
    for table in tables:
        EXPORT_FORMATS[(table, file_type)] = fmt
EXPORT_HEADERS = {}
for data_type, file_type in EXPORT_FORMATS:
    EXPORT_HEADERS[(data_type, file_type)] = HEADER_TEMPLATES[file_type]

for data_type, fields in CSV_EXPORT_FORMATS.iteritems():
    tup = (data_type, "csv")
    EXPORT_FORMATS[tup] = ','.join(["%("+f+")s" for f in fields])
    EXPORT_HEADERS[tup] = ','.join(fields)

# regions should be displayed spread out with their annotation
# since they may overlap, and since some colors are used twice
# (pack) and copies should be displayed just using the color since
# they don't overlap and the color is unambiguous for copy number
# (dense). bedGraph probes should be displayed in full so you can
# see the scatterplot, and segments can be displayed dense using a
# grayscale color code over the entire genomic space.
EXPORT_VISIBILITY = {
    "regions": "pack",
    "segments": "dense",
    "copies": "dense",
    "breaks": "pack",
    }

ALTERED = ("loss", "gain", "deletion", "amplification")

ZOOM_FACTORS = (3, 10)


@view_config(route_name="links", renderer="templates/profile_links.pt")
@check_userprofiles
def links(request):
    """Show a list of breakpoints and copy number alterations."""
    names = request.matchdict["name"]
    namelist = names.split(',')
    alterations = []
    export = ""
    export_db = ""
    userid = authenticated_userid(request)
    for name in namelist:
        pro = db.Profile(name)
        copies = pro.copies(userid)
        tables = (
            #("breaks",pro.breaks(userid)),
            ("copies", [a for a in copies if a["annotation"] in ALTERED]),
            )
        added = False
        for table, dicts in tables:
            for d in dicts:
                added = True
                d["name"] = name
                d["type"] = table
                d["size"] = d["max"]-d["min"]
                d["size_kb"] = d["size"]/1000
                mid = (d["max"]+d["min"])/2
                d["zoom"] = []
                for f in ZOOM_FACTORS:
                    width = f * d["size"]/2
                    d["zoom"].append({
                        "min": max(mid-width, 1),
                        "max": mid+width,
                        })
                alterations.append(d)
        # If any added for this profile, add it to the export form.
        if added:
            ex = pro.get_export(userid)
            if ex["export"] == "yes":
                export_db = ex["db"]
                export += ex["ucsc"]
    alterations.sort(key=lambda d: (
        d["name"],
        db.ChromLengths.CHROM_RANK[d["chromosome"]],
        d["min"]))
    return {
        "export": export,
        "db": export_db,
        "alterations": alterations,
        "user": userid,
        "zoom": ZOOM_FACTORS,
        "names": names,
        }


@view_config(route_name="export")
@check_export
def export(request):
    """export annotations and models in plain text formats.

    Access rights: for public profiles, everyone can read everyone
    else's annotations and models. That way we can have a button for
    export to UCSC.

    For non-public profiles, deny un-authorized access to annotations
    and models as well.

    """
    # oldargs=,user_id,profile_id,table,file_format)

    # mdkeys user name what format
    md = request.matchdict
    pro = db.Profile(md["name"])
    fun = getattr(pro, md["what"])
    # need to
    dicts = fun(md["user"])
    pinfo = pro.get()
    pinfo["table"] = md["what"]
    pinfo["visibility"] = EXPORT_VISIBILITY[md["what"]]
    for d in dicts:
        d["user_id"] = md["user"]
        d["profile_id"] = md["name"]
    response = respond_bed_csv(md["what"], md["format"], pinfo, dicts)
    return response


def respond_bed_csv(table, fmt, hinfo, dicts):
    response = Response(content_type="text/plain")
    tup = (table, fmt)
    header_tmp = EXPORT_HEADERS[tup]
    header = header_tmp % hinfo + '\n'
    response.write(header)
    fmt = EXPORT_FORMATS[tup]
    for d in dicts:
        line = fmt % d + "\n"
        response.write(line)
    return response
