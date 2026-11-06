"""Add a finished event from data/points.json to data/reference.json as a past event.

usage: python3 tools/add_event_reference.py <points event key> <reference key> <label>
  e.g. python3 tools/add_event_reference.py 20261031-1200_20261106-2059 2026-10-31 3周年

Writes, for every idol and rank (1/10/12/50/100/500/SS):
  refs   : [pct, final/border] curve, about hourly, denser in the last 1%, ending at [100, 1]
  finals : final border (last post)
  past   : border on a 1% grid (None before the first post, [100] = final)
Re-running with the same reference key replaces that event's data.
"""
import json, sys, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
COL = {"1": 2, "12": 3, "50": 4, "100": 5, "500": 6, "10": 7, "SS": 8}
RANKS = ["100", "500", "1", "10", "12", "50", "SS"]


def lerp(pts, x):
    if not pts or x < pts[0][0]: return None
    if x >= pts[-1][0]: return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return None


def main(pkey, rkey, label):
    P = json.load(open(os.path.join(ROOT, "data/points.json"), encoding="utf-8"))
    rpath = os.path.join(ROOT, "data/reference.json")
    R = json.load(open(rpath, encoding="utf-8"))
    ev = P[pkey]
    hour = 100 / ((__import__("datetime").datetime.fromisoformat(ev["end"]) -
                   __import__("datetime").datetime.fromisoformat(ev["start"])).total_seconds() / 3600 + 1 / 60)
    R["refs"] = [x for x in R["refs"] if x["event"] != rkey]
    n_refs = 0
    for idol, rows in ev["idols"].items():
        rows = sorted(rows, key=lambda p: p[1])
        for rk in RANKS:
            ci = COL[rk]
            pts = [(p[1], p[ci]) for p in rows if p[ci] is not None]
            if not pts: continue
            final = pts[-1][1]
            R["finals"].setdefault(idol, {}).setdefault(rkey, {})[rk] = final
            grid = [None if lerp(pts, x) is None else round(lerp(pts, x)) for x in range(101)]
            grid[100] = final
            R["past"].setdefault(idol, {}).setdefault(rkey, {})[rk] = grid
            curve, last = [], -9
            for i, (x, v) in enumerate(pts):
                tail = x >= 99.0
                if (x - last >= hour * 0.95 or (tail and x - last >= 0.15) or i == len(pts) - 1) and v > 0:
                    curve.append([round(x, 2), round(final / v, 4)]); last = x
            if curve and curve[-1][0] < 100: curve.append([100.0, 1.0])
            if len(curve) > 1:
                R["refs"].append({"event": rkey, "title": ev["title"], "idol": idol, "rank": rk, "curve": curve}); n_refs += 1
    R["events"] = [e for e in R["events"] if e["key"] != rkey] + [{"key": rkey, "label": label}]
    json.dump(R, open(rpath, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{label}: refs {n_refs}, idols {len(ev['idols'])}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
