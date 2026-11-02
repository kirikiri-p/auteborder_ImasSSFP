"""Prediction model shared by merge_export.py and record_daily.py (index.html does the same in JS).

pred = sqrt(A x B), the geometric mean of
  A  border now x median over 2.5周年's curves of (final / border) at the same elapsed %  (level; same schedule as now, so the time of day lines up)
  B  border now + (border now - border 24 h ago) x M(p)                                     (this event's pace)
     M(p) = median over past curves of (final - border(p)) / (border(p) - border(p - 24 h)); 24 h in each event's own %
When there is no post 24 h back, pred = A.
Goal margins m90(p): the 90th percentile of final / pred when one past event predicts the other, made non-increasing
in p. Grids live in data/model.json (python3 tools/model.py rebuilds it from data/reference.json).
Past event lengths: 2.5周年 5/9 12:00-5/15 20:59 (152.98 h); 2周年 assumed 11/1 12:00-11/6 20:59 (128.98 h).
"""
import datetime as dt, json, math, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURS = {"2026-05-09": 152.98, "2025-11-01": 128.98}
LEVEL_EVENT = "2026-05-09"   # level part: only the past event with the same schedule (12:00 start, 20:59 end, 6.4 days), so the clock lines up
COL = {"1": 2, "12": 3, "50": 4, "100": 5, "500": 6, "10": 7, "SS": 8}

def ratio(c, p):
    if p < c[0][0] or p > 100: return None
    for i in range(1, len(c)):
        if c[i][0] >= p:
            a, b = c[i-1], c[i]; return a[1] + (b[1]-a[1])*(p-a[0])/(b[0]-a[0]) if b[0] > a[0] else b[1]
    return 1

def _build():
    R = json.load(open(os.path.join(ROOT, "data/reference.json")))
    C = {}
    for z in R["refs"]: C.setdefault((z["event"], z["rank"]), []).append(z["curve"])
    grid = [round(x * 0.5, 1) for x in range(2, 201)]
    out = {"note": __doc__.strip().splitlines()[0], "hours": HOURS, "grid": grid, "ranks": {}}
    for rk in sorted({k[1] for k in C}):
        Ms, m90 = [], []
        for p in grid:
            vals = []
            for ev, T in HOURS.items():
                d = 24 / T * 100
                for c in C.get((ev, rk), []):
                    x, y = ratio(c, p), ratio(c, p - d) if p - d >= c[0][0] else None
                    if x and y and 1/x > 1/y: vals.append((1 - 1/x) / (1/x - 1/y))
            Ms.append(round(st.median(vals), 4) if len(vals) >= 10 else None)
        out["ranks"][rk] = {"M": Ms}
        mx = []
        for i, p in enumerate(grid):   # cross-event coverage of the mixed prediction
            cov = []
            for A, B in (("2026-05-09", "2025-11-01"), ("2025-11-01", "2026-05-09")):
                rB = [r for r in (ratio(c, p) for c in C.get((B, rk), [])) if r]
                if not rB: continue
                mR = st.median(rB)
                vB = []
                for c in C.get((B, rk), []):
                    d = 24 / HOURS[B] * 100; x, y = ratio(c, p), ratio(c, p - d) if p - d >= c[0][0] else None
                    if x and y and 1/x > 1/y: vB.append((1 - 1/x) / (1/x - 1/y))
                M = st.median(vB) if len(vB) >= 5 else None
                for c in C.get((A, rk), []):
                    x = ratio(c, p)
                    if not x: continue
                    b = 1 / x; pa = b * mR; pr = pa
                    d = 24 / HOURS[A] * 100; y = ratio(c, p - d) if p - d >= c[0][0] else None
                    if M and y: pr = math.sqrt(pa * (b + (b - 1/y) * M))
                    cov.append(1 / pr)
            cov.sort(); m90.append(cov[int(0.9 * (len(cov) - 1))] if len(cov) >= 10 else None); mx.append(cov[-1] if len(cov) >= 10 else None)
        for name, arr in (("m90", m90), ("mmax", mx)):   # non-increasing in p, at least 1
            env, run = [None] * len(grid), 1.0
            for i in range(len(grid) - 1, -1, -1):
                if arr[i] is not None: run = max(run, arr[i])
                env[i] = round(run, 4)
            out["ranks"][rk][name] = env
    json.dump(out, open(os.path.join(ROOT, "data/model.json"), "w"), indent=0)
    return out

_M = None
def model():
    global _M
    if _M is None: _M = json.load(open(os.path.join(ROOT, "data/model.json")))
    return _M

def at(arr, p):
    g = model()["grid"]
    if p <= g[0]: return arr[0]
    if p >= g[-1]: return arr[-1]
    i = int((p - g[0]) / 0.5); a, b = arr[i], arr[min(i + 1, len(arr) - 1)]
    if a is None or b is None: return a if b is None else b
    return a + (b - a) * (p - g[i]) / 0.5

_R = None; _MR = {}
def medratio(rk, p):
    global _R
    if (rk, p) in _MR: return _MR[(rk, p)]
    if _R is None: _R = json.load(open(os.path.join(ROOT, "data/reference.json")))
    rs = [r for r in (ratio(z["curve"], p) for z in _R["refs"] if z["rank"] == rk and z["event"] == LEVEL_EVENT) if r]
    _MR[(rk, p)] = st.median(rs) if rs else None
    return _MR[(rk, p)]

def pred(rows, rk, upto=None):
    """rows: the event's points for one idol. Returns (pred, row used) for the last row at or before upto."""
    ci = COL[rk]; rows = [r for r in rows if r[ci] and (upto is None or r[0] <= upto)]
    if not rows: return None, None
    lp = rows[-1]
    if lp[1] >= 99.99: return lp[ci], lp
    mr = medratio(rk, lp[1])
    if not mr: return None, lp
    a = lp[ci] * mr
    t24 = (dt.datetime.strptime(lp[0], "%Y-%m-%d %H:%M") - dt.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    old = [r for r in rows if r[0] <= t24]
    M = at(model()["ranks"][rk]["M"], lp[1])
    if not old or M is None: return a, lp
    b = lp[ci] + max(0, lp[ci] - old[-1][ci]) * M
    return math.sqrt(a * b), lp

def margin(rk, p): return at(model()["ranks"][rk]["m90"], p)
def bound(rk, p): return at(model()["ranks"][rk]["mmax"], p)

def safe_line(rows, rk, step_h=3):
    """'Safe line': the largest final the past events allow, pred x mmax(p) (the worst miss seen when one past
    event predicted the other). Kept as a running minimum over the posts every step_h hours, so it only comes
    down as the end nears; if the prediction now x m90 rises above it, the bound was broken and it restarts there.
    Returns (line, broken)."""
    ci = COL[rk]; rows = [r for r in rows if r[ci]]
    if not rows: return None, False
    line = None; broken = False; last = None
    for i, r in enumerate(rows):
        t = dt.datetime.strptime(r[0], "%Y-%m-%d %H:%M")
        if i != len(rows) - 1 and last and (t - last).total_seconds() < step_h * 3600: continue
        last = t
        p, lp = pred(rows[:i + 1], rk)
        if not p: continue
        u = p * bound(rk, lp[1])
        if line is None or u < line: line = u
        if p * margin(rk, lp[1]) > line: line, broken = u, (i == len(rows) - 1) or broken
    return round(line), broken

if __name__ == "__main__":
    o = _build()
    for rk in ("100", "500"):
        print(rk, [(p, o["ranks"][rk]["m90"][o["grid"].index(p)]) for p in (20.0, 30.0, 40.0, 50.0, 60.0, 75.0, 84.0, 95.0, 98.5, 100.0)])
