from PIL import Image, ImageDraw

def normalize(x,xmax,m=None,M=None):
    """Scale values to an integer in [0,xmax]."""
    if m is None:
        m = x.min()
    if M is None:
        M = x.max()
    return ((x-m)/float(M-m)*xmax).astype(int)

def draw(arrays, fn, width, height, 
         lr_min=None, lr_max=None, pos_min=None, pos_max=None):
    """Draw a PNG scatterplot width x height pixels.

    arrays["chromStart"] should be numpy int and arrays["logratio"]
    should be numpy float.

    lr_min, lr_max give optional y axis limits, pos_min, pos_max give
    optional x axis limits.

    """
    pos_px = normalize(arrays["chromStart"], width-1, pos_min, pos_max)
    lr_px = height - normalize(arrays["logratio"], height-1, lr_min, lr_max)-1
    #print pos_px.max(), width
    # "1" means black/white image.
    im = Image.new("1",(width,height),1)
    draw = ImageDraw.Draw(im)
    draw.point(zip(pos_px,lr_px))
    #draw.line(zip(pos_px,lr_px))
    # draw +
    # for xdiff in -1, 1:
    #     draw.point(zip(pos_px+xdiff,lr_px))
    # for ydiff in -1, 1:
    #     draw.point(zip(pos_px,lr_px+ydiff))

    # draw x
    for xdiff in -1, 1, -2, 2:
        for ydiff in -1, 1, -2, 2:
            draw.point(zip(pos_px+xdiff,lr_px+ydiff))
    im.save(fn, "PNG")

if __name__ == "__main__":
    import csv,numpy,os
    f=open("chr2.csv")
    r = csv.reader(f)
    r.next()
    positions = []
    logratios = []
    for pos, lr  in r:
        positions.append(int(pos))
        logratios.append(float(lr))
    arrays = {
        "chromStart":numpy.array(positions),
        "logratio":numpy.array(logratios),
    }
    table = "<table>%s</table>"
    rows = []
    # 30 000 seems like the biggest image size that firefox on ubuntu
    # will display. Same on firefox windows.

    #chrome windows max 300 000.

    #chrome/safari on ipad max 20 000.

    #chrome on ubuntu 1 000 000.
    
    widths = [5000,10000,20000,30000,35000,50000]
    for fac in 1,2,3,4,5,6,8,10,12:
        widths.append(len(positions)*fac)
    for w in widths:
        fn = "chr2_%dx200.png"%w
        if not os.path.isfile(fn):
            draw(arrays, fn, w, 200)
        row = '<tr><td>%s</td><td><img src="%s" /></td></tr>'%(w,fn)
        rows.append(row)
    print table%'\n'.join(rows)
