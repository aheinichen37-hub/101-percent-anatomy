"""Crop new textbook figures from the OpenStax PDF into figs/ and register them in caps.json.

Usage: python3 tools/idimg/add_figures.py 13.23:554 11.9:435 ...   (figure:pdf page index)

The drawing is the union of image objects sitting between the previous caption on the page
and this figure's own "FIGURE n.m" caption. Cropped at render scale 2.4, like the v2.4 build.
"""
import json, os, re, sys
import pypdfium2 as pdfium, pypdfium2.raw as raw
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PDF = os.environ.get("ANATOMY_PDF", "/mnt/user-data/uploads/Claude/a&p open stax 1-100.pdf")
SCALE = 2.4

def captions(pg):
    tp = pg.get_textpage(); H = pg.get_height(); out = []
    s = tp.search("FIGURE ", match_case=True)
    while True:
        r = s.get_next()
        if r is None: break
        m = re.match(r"FIGURE\s+(\d+\.\d+)", tp.get_text_range(r[0], 40))
        if m:
            l, b, rr, t = tp.get_charbox(r[0]); out.append((m.group(1), (H - t) * SCALE))
    return sorted(out, key=lambda c: c[1])

def images(pg):
    H = pg.get_height(); out = []
    for o in pg.get_objects(filter=[raw.FPDF_PAGEOBJ_IMAGE]):
        l, b, r, t = o.get_bounds()
        if (r - l) * (t - b) >= 100 * 100:
            out.append((l * SCALE, (H - t) * SCALE, r * SCALE, (H - b) * SCALE))
    return out

def crop(doc, fig, page):
    pg = doc[page]; caps = captions(pg)
    me = [c for c in caps if c[0] == fig]
    if not me: raise SystemExit(f"{fig}: no caption on page {page}")
    top_cap = me[0][1]
    prev = [c[1] for c in caps if c[1] < top_cap]
    region_top = (max(prev) + 110) if prev else 0
    ims = [i for i in images(pg) if i[1] >= region_top - 10 and i[3] <= top_cap + 10]
    if not ims: raise SystemExit(f"{fig}: no image above its caption on page {page}")
    x0 = min(i[0] for i in ims) - 6; y0 = min(i[1] for i in ims) - 6
    x1 = max(i[2] for i in ims) + 6; y1 = max(i[3] for i in ims) + 6
    img = pg.render(scale=SCALE).to_pil().convert("RGB")
    box = (max(0, int(x0)), max(0, int(y0)), min(img.width, int(x1)), min(img.height, int(y1)))
    return img.crop(box)

if __name__ == "__main__":
    doc = pdfium.PdfDocument(PDF)
    caps_path = os.path.join(HERE, "caps.json")
    caps = json.load(open(caps_path))
    for arg in sys.argv[1:]:
        fig, page = arg.split(":"); page = int(page)
        im = crop(doc, fig, page)
        im.save(os.path.join(REPO, "figs", f"{fig}.jpg"), quality=85, optimize=True)
        caps.setdefault(fig, [])
        if page not in caps[fig]: caps[fig].append(page)
        print(fig, im.size)
    json.dump(caps, open(caps_path, "w"), indent=1, sort_keys=True)
