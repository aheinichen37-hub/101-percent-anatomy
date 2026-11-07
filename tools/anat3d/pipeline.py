"""Card pictures from BodyParts3D: pick the best view, peel away muscles in the way, frame, and write the three
files the game expects (figs/id/<card>-q.jpg, -m.png, -a.jpg).

Colours: bone cream, other muscles salmon, selected structure #00c3ff (see render.py).
Credit: BodyParts3D (c) The Database Center for Life Science, CC BY-SA 2.1 Japan.
"""
import collections, os, re
import cv2
import numpy as np
from PIL import Image

from .render import BONE, HIGHLIGHT, MUSCLE, read_stl

# (azimuth, elevation); camera looks along +y after rotating the body by az about the vertical axis
SEARCH_VIEWS = {"front": (0, 6), "back": (180, 6), "right": (-90, 6), "left": (90, 6),
                "front-right": (-38, 10), "front-left": (38, 10), "back-right": (-142, 10), "back-left": (142, 10),
                "below": (0, -72), "above": (0, 72)}
CANON = {"front", "back", "right", "left"}


def rot(az, el):
    a, e = np.radians(az), np.radians(el)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]], np.float32)
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]], np.float32)
    return Rx @ Rz


class Scene:
    def __init__(self, data_dir):
        self.dir = data_dir
        self.names = {}
        for line in open(os.path.join(data_dir, "parts_list_e.txt"), encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) == 2 and os.path.exists(os.path.join(data_dir, "stl", p[0] + ".stl")):
                self.names[p[0]] = p[1].strip().lower()
        kids = collections.defaultdict(set)
        for line in open(os.path.join(data_dir, "conventional_part_of.txt"), encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 4 and p[0].startswith("FMA"):
                kids[p[0]].add(p[2])

        def below(root):
            seen, st = set(), [root]
            while st:
                for y in kids.get(st.pop(), ()):
                    if y not in seen:
                        seen.add(y); st.append(y)
            return seen & set(self.names)
        self.bones = sorted(below("FMA23881"))     # skeletal system
        self.muscles = sorted(below("FMA72954"))   # muscular system
        self._m, self._bb, self._px = {}, {}, {}

    def side(self, bp):
        n = self.names[bp]
        return "L" if re.search(r"\bleft\b", n) else "R" if re.search(r"\bright\b", n) else "M"

    def mesh(self, bp):
        if bp not in self._m:
            t = read_stl(os.path.join(self.dir, "stl", bp + ".stl"))
            self._m[bp] = t
            v = t.reshape(-1, 3)
            self._bb[bp] = (v.min(0), v.max(0))
        return self._m[bp]

    def bbox(self, bp):
        self.mesh(bp)
        return self._bb[bp]

    def proxy(self, bp, keep=5, grow=2.3):
        key = (bp, keep, grow)
        """Every `keep`th triangle, enlarged so the gaps close: a cheap stand-in for visibility tests."""
        if key not in self._px:
            t = self.mesh(bp)[::keep]
            c = t.mean(1, keepdims=True)
            self._px[key] = (c + (t - c) * grow).astype(np.float32)
        return self._px[key]


def _corners(lo, hi):
    return np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], np.float32)


def raster(scene, parts, R, cx, cz, S, N, colors=None, proxy=False, light=0.75, bg=(255, 255, 255)):
    """Draw `parts` (bp list). With `colors` {bp: rgb} returns an RGB image; otherwise an id map (index+1 into parts)."""
    tris, cols, ids = [], [], []
    half = S / 2 * 1.02
    for i, bp in enumerate(parts):
        lo, hi = scene.bbox(bp)
        cc = _corners(lo, hi) @ R.T
        if cc[:, 0].max() < cx - half or cc[:, 0].min() > cx + half or cc[:, 2].max() < cz - half or cc[:, 2].min() > cz + half:
            continue
        t = (scene.proxy(bp) if proxy else scene.mesh(bp)) @ R.T
        tris.append(t)
        n = len(t)
        ids.append(np.full(n, i + 1, np.int32))
        if colors is not None:
            cols.append(np.tile(np.array(colors[bp], np.float32), (n, 1)))
    if not tris:
        return np.full((N, N, 3), bg, np.uint8) if colors is not None else np.zeros((N, N), np.int32)
    T = np.concatenate(tris)
    ID = np.concatenate(ids)
    sc = N / S
    px = (T[:, :, 0] - cx) * sc + N / 2
    py = N / 2 - (T[:, :, 2] - cz) * sc
    keep = (px.max(1) > -4) & (px.min(1) < N + 4) & (py.max(1) > -4) & (py.min(1) < N + 4)
    T, ID, px, py = T[keep], ID[keep], px[keep], py[keep]
    depth = T[:, :, 1].mean(1)
    order = np.argsort(-depth)
    P = np.stack([px, py], -1).astype(np.int32)
    if colors is not None:
        nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
        shade = (1 - light) + light * np.abs(nrm[:, 1])
        C = np.concatenate(cols)[keep]
        C = np.clip(C * shade[:, None], 0, 255).astype(np.uint8)
        canvas = np.full((N, N, 3), bg, np.uint8)
        for i in order:
            cv2.fillConvexPoly(canvas, P[i], (int(C[i, 0]), int(C[i, 1]), int(C[i, 2])))
        return canvas
    canvas = np.zeros((N, N, 3), np.uint8)
    for i in order:
        v = int(ID[i])
        cv2.fillConvexPoly(canvas, P[i], (v & 255, (v >> 8) & 255, v >> 16))
    return canvas[:, :, 0].astype(np.int32) | (canvas[:, :, 1].astype(np.int32) << 8) | (canvas[:, :, 2].astype(np.int32) << 16)


def splat_ids(scene, parts, R, cx, cz, S, N):
    """Fast visibility map (index+1 per pixel) from point samples; good enough to choose views and find occluders."""
    pts, ids = [], []
    half = S / 2 * 1.02
    for i, bp in enumerate(parts):
        lo, hi = scene.bbox(bp)
        cc = _corners(lo, hi) @ R.T
        if cc[:, 0].max() < cx - half or cc[:, 0].min() > cx + half or cc[:, 2].max() < cz - half or cc[:, 2].min() > cz + half:
            continue
        t = scene.proxy(bp, keep=4, grow=1.0)
        p = np.concatenate([t.mean(1, keepdims=True), t]).reshape(-1, 3) if False else np.concatenate([t.mean(1), t.reshape(-1, 3)])
        p = p @ R.T
        pts.append(p)
        ids.append(np.full(len(p), i + 1, np.int32))
    if not pts:
        return np.zeros((N, N), np.int32)
    P = np.concatenate(pts)
    I = np.concatenate(ids)
    sc = N / S
    x = ((P[:, 0] - cx) * sc + N / 2).astype(np.int32)
    y = (N / 2 - (P[:, 2] - cz) * sc).astype(np.int32)
    ok = (x >= 0) & (x < N) & (y >= 0) & (y < N)
    x, y, I, d = x[ok], y[ok], I[ok], P[ok, 1]
    order = np.argsort(-d)                    # far first, near overwrites
    idm = np.zeros(N * N, np.int32)
    idm[(y * N + x)[order]] = I[order]
    idm = idm.reshape(N, N)
    # close pinholes: a hole takes its neighbour's id (3x3 max)
    dil = cv2.dilate(idm.astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32)
    return np.where(idm == 0, dil, idm)


def frame_for(scene, target, R):
    """Centre (view coords) and size of the picture window for a target."""
    lo = np.min([scene.bbox(b)[0] for b in target], 0)
    hi = np.max([scene.bbox(b)[1] for b in target], 0)
    d = float(max(hi - lo))
    S = max(70.0 if d < 30 else 105.0, d * 1.8 if d <= 120 else 216 + (d - 120) * 0.9)
    cc = _corners(lo, hi) @ R.T
    cx = float((cc[:, 0].min() + cc[:, 0].max()) / 2)
    cz = float((cc[:, 2].min() + cc[:, 2].max()) / 2)
    return cx, cz, S, d


def context_for(scene, target, R, cx, cz, S, with_muscles, side_policy):
    pool = scene.bones + (scene.muscles if with_muscles else [])
    tset = set(target)
    half = S / 2 * 1.05
    out = []
    for bp in pool:
        if bp in tset:
            continue
        if side_policy == "right" and scene.side(bp) == "L":
            continue
        lo, hi = scene.bbox(bp)
        cc = _corners(lo, hi) @ R.T
        if cc[:, 0].max() < cx - half or cc[:, 0].min() > cx + half or cc[:, 2].max() < cz - half or cc[:, 2].min() > cz + half:
            continue
        out.append(bp)
    return out


def choose_view(scene, target, with_muscles, side_policy, N=200, want=None):
    """Best (view, removed muscles) by visible target area, peeling occluding muscles when the target is buried."""
    muscles = set(scene.muscles)
    best = None
    for view, (az, el) in SEARCH_VIEWS.items():
        R = rot(az, el)
        cx, cz, S, d = frame_for(scene, target, R)
        ctx = context_for(scene, target, R, cx, cz, S, with_muscles, side_policy)
        sil_ids = splat_ids(scene, list(target), R, cx, cz, S, N)
        sil = sil_ids > 0
        sil_n = int(sil.sum())
        if sil_n < 20:
            continue
        removed, rounds, vis_n = set(), 0, 0
        while True:
            parts = [b for b in ctx if b not in removed] + list(target)
            idm = splat_ids(scene, parts, R, cx, cz, S, N)
            tid = set(range(len(parts) - len(target) + 1, len(parts) + 1))
            vis = np.isin(idm, list(tid))
            vis_n = int(vis.sum())
            if vis_n / sil_n >= 0.6 or rounds >= 4:
                break
            hit = collections.Counter(idm[sil & ~vis].tolist())
            occ = [parts[i - 1] for i, n in hit.items() if i > 0 and n >= 0.03 * sil_n and (parts[i - 1] in muscles or rounds >= 1 or not with_muscles)]
            if not occ:
                break
            removed.update(occ)
            rounds += 1
        score = vis_n * (0.65 ** rounds) * (0.985 ** len(removed)) * (1.06 if view in CANON else 1.0) * (1.03 if view == 'front' else 1.0)
        if best is None or score > best["score"]:
            best = {"view": view, "removed": removed, "score": score, "ratio": vis_n / sil_n, "rounds": rounds}
    return best


def render_card(scene, target, name, out_base, with_muscles, side_policy, size=720):
    """Pick the view, draw the picture, write -q.jpg, -m.png and -a.jpg. Returns a report dict."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from idimg import highlight
    best = choose_view(scene, target, with_muscles, side_policy)
    if best is None:
        return {"status": "fail", "reason": "target not visible in any view"}
    az, el = SEARCH_VIEWS[best["view"]]
    R = rot(az, el)
    cx, cz, S, d = frame_for(scene, target, R)
    ctx = [b for b in context_for(scene, target, R, cx, cz, S, with_muscles, side_policy) if b not in best["removed"]]
    colors = {b: (MUSCLE if b in set(scene.muscles) else BONE) for b in ctx}
    colors.update({b: HIGHLIGHT for b in target})
    parts = ctx + list(target)
    big = raster(scene, parts, R, cx, cz, S, size * (2 if S < 450 else 1), colors=colors)
    img = cv2.resize(big, (size, size), interpolation=cv2.INTER_AREA)
    idm = raster(scene, parts, R, cx, cz, S, size)
    tid = list(range(len(ctx) + 1, len(parts) + 1))
    mask = np.isin(idm, tid)
    frac = float(mask.mean())
    if frac < 0.002:
        return {"status": "fail", "reason": f"highlight too small ({frac:.4f})"}
    if frac > 0.6:
        return {"status": "fail", "reason": f"highlight covers {frac:.0%}"}
    m8 = cv2.GaussianBlur((mask * 255).astype(np.uint8), (0, 0), 0.8)
    ys, xs = np.nonzero(mask)
    cy, cxp = ys.mean(), xs.mean()
    k = int(np.argmin((ys - cy) ** 2 + (xs - cxp) ** 2))
    point = (int(xs[k]), int(ys[k]))
    pan = Image.fromarray(img)
    mimg = Image.fromarray(m8, "L")
    rgba = Image.new("RGBA", pan.size, HIGHLIGHT + (0,))
    rgba.putalpha(mimg)
    ans = highlight.answer_image(pan, mimg, "blob", name, point)
    pan.save(out_base + "-q.jpg", quality=84, optimize=True)
    rgba.save(out_base + "-m.png", optimize=True)
    ans.convert("RGB").save(out_base + "-a.jpg", quality=84, optimize=True)
    return {"status": "ok", "view": best["view"], "peeled": len(best["removed"]), "ratio": round(best["ratio"], 2),
            "frame_mm": round(S), "frac": round(frac, 3)}
