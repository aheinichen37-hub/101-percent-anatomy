"""Tiny numpy/OpenCV renderer for BodyParts3D structures (CC BY-SA 2.1 JP, (c) DBCLS).

No Blender or GPU needed. Triangles are sorted back to front (painter's algorithm), Lambert-shaded with a
headlight, drawn at 2x and shrunk for smooth edges.

    from anat3d.render import Atlas
    at = Atlas("/path/to/BodyParts3D/assets/BodyParts3D_data")
    bps = at.find("frontal bone")                 # -> ["FMA52734", ...] (left/right/composite)
    img = at.render({bp: (200,200,200) for bp in all}, highlight={...: (255,60,90)}, view="front")
"""
import os, re
import cv2
import numpy as np

VIEWS = {  # (azimuth deg about the vertical axis, elevation deg)
    "front": (0, 0), "back": (180, 0), "left": (90, 0), "right": (-90, 0),
    "front-left": (35, 8), "front-right": (-35, 8), "top": (0, 85), "below": (0, -85)}


def read_stl(path):
    d = open(path, "rb").read()
    n = int.from_bytes(d[80:84], "little")
    a = np.frombuffer(d[84:84 + 50 * n], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return a["v"].reshape(-1, 3, 3).astype(np.float32)


class Atlas:
    def __init__(self, data_dir):
        self.dir = data_dir
        self.names = {}
        for line in open(os.path.join(data_dir, "parts_list_e.txt"), encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) == 2 and os.path.exists(os.path.join(data_dir, "stl", p[0] + ".stl")):
                self.names[p[0]] = p[1].strip().lower()
        self._cache = {}

    def find(self, pattern):
        rx = re.compile(pattern, re.I)
        return [b for b, n in sorted(self.names.items()) if rx.search(n)]

    def mesh(self, bp):
        if bp not in self._cache:
            self._cache[bp] = read_stl(os.path.join(self.dir, "stl", bp + ".stl"))
        return self._cache[bp]

    def render(self, colors, view="front", size=900, bounds=None, bg=(255, 255, 255), highlight=None, light=0.75):
        """colors: {bp: (r,g,b)}; highlight: {bp: (r,g,b)} drawn in those colors (and kept in the framing).
        bounds: (min3, max3) to fix the framing between renders."""
        parts = dict(colors)
        parts.update(highlight or {})
        az, el = VIEWS.get(view, view) if isinstance(view, str) else view
        a, e = np.radians(az), np.radians(el)
        # world: x = patient left->right?, y = front/back, z = up. Camera looks along +y after rotating by az.
        Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]], np.float32)
        Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]], np.float32)
        R = Rx @ Rz
        tris, cols = [], []
        for bp, c in parts.items():
            t = self.mesh(bp) @ R.T
            tris.append(t)
            cols.append(np.tile(np.array(c, np.float32), (len(t), 1)))
        T = np.concatenate(tris)
        C = np.concatenate(cols)
        if bounds is None:
            lo, hi = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0)
        else:
            lo, hi = (np.array(bounds[0]) @ R.T), (np.array(bounds[1]) @ R.T)
            lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
        S = size * 2
        span = max(hi[0] - lo[0], hi[2] - lo[2]) * 1.06
        scale = S / span
        cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
        px = (T[:, :, 0] - cx) * scale + S / 2
        py = S / 2 - (T[:, :, 2] - cz) * scale
        nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        nl = np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
        nrm = nrm / nl
        facing = np.abs(nrm[:, 1])                     # camera along y: headlight shading
        shade = (1 - light) + light * facing
        depth = T[:, :, 1].mean(1)
        order = np.argsort(-depth)                      # far (large y) first
        canvas = np.full((S, S, 3), bg, np.uint8)
        pts = np.stack([px, py], -1).astype(np.int32)
        col = np.clip(C * shade[:, None], 0, 255).astype(np.uint8)
        for i in order:
            cv2.fillConvexPoly(canvas, pts[i], tuple(int(x) for x in col[i]), lineType=cv2.LINE_8)
        return cv2.resize(canvas, (size, size), interpolation=cv2.INTER_AREA)

    def bounds(self, bps):
        lo = np.min([self.mesh(b).reshape(-1, 3).min(0) for b in bps], 0)
        hi = np.max([self.mesh(b).reshape(-1, 3).max(0) for b in bps], 0)
        return lo, hi
