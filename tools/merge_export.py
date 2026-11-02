"""Merge border exports and/or my fan counts into data/, then rebuild data/latest.txt.

  python3 tools/merge_export.py --borders exp.txt          # lines from __export(): name|MMDDHHMM,1,12,50,100,500,10,SS;...
  python3 tools/merge_export.py --my "2026-11-02 14:37" scores.json   # {"幽谷霧子": 2342960, ...} (all 28)
Prints what changed, the 500th goals still open (data/goals.json) and idols whose 500th prediction is now above
the recorded 0:00 one (pred500). Commit and push afterwards.
"""
import argparse, datetime as dt, json, os, statistics as st, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
KEY = "20261031-1200_20261106-2059"; S0 = dt.datetime(2026, 10, 31, 12); E0 = dt.datetime(2026, 11, 6, 20, 59)
ap = argparse.ArgumentParser(); ap.add_argument("--borders"); ap.add_argument("--my", nargs=2); a = ap.parse_args()
P = json.load(open("data/points.json", encoding="utf-8")); ev = P[KEY]["idols"]
if a.borders:
    added = 0
    for line in open(a.borders, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        name, body = line.split("|"); have = {r[0] for r in ev[name]}
        for rec in filter(None, body.split(";")):
            v = rec.split(","); c = v[0]; d = dt.datetime(2026, int(c[:2]), int(c[2:4]), int(c[4:6]), int(c[6:8]))
            t = d.strftime("%Y-%m-%d %H:%M")
            if t in have: continue
            ev[name].append([t, round((d - S0).total_seconds() / (E0 - S0).total_seconds() * 100, 2)] + [int(x) if x not in ("", "null") else None for x in v[1:]]); added += 1
        ev[name].sort(key=lambda r: r[0])
    open("data/points.json", "w", encoding="utf-8").write(json.dumps(P, ensure_ascii=False, indent=1) + "\n")
    import collect; collect.write_latest(P)
    print("borders added", added, "| last", sorted({v[-1][0] for v in ev.values()}))
M = json.load(open("data/my.json", encoding="utf-8")); my = M["history"][-1]["scores"]
if a.my:
    s = json.load(open(a.my[1], encoding="utf-8")); assert set(s) == set(my), set(my) ^ set(s)
    for k in s:
        if s[k] != my[k]: print(k, my[k], "->", s[k], "+%d" % (s[k] - my[k]), "DOWN?" if s[k] < my[k] else "")
    M["history"].append({"time": a.my[0], "scores": s}); my = s
    open("data/my.json", "w", encoding="utf-8").write(json.dumps(M, ensure_ascii=False, indent=1) + "\n")
G = json.load(open("data/goals.json", encoding="utf-8")); R = json.load(open("data/reference.json"))
def ratio(c, p):
    if p < c[0][0]: return None
    for i in range(1, len(c)):
        if c[i][0] >= p:
            x, y = c[i-1], c[i]; return x[1] + (y[1]-x[1])*(p-x[0])/(y[0]-x[0]) if y[0] > x[0] else y[1]
    return 1
left = {n: g - my[n] for n, g in G["goals"].items() if g > my[n]}
print("500 goals open: %.1f万" % (sum(left.values()) / 1e4), {n: round(v / 1e4, 1) for n, v in sorted(left.items(), key=lambda x: -x[1])})
up = []
for n, rec in G.get("pred500", {}).items():
    lp = ev[n][-1]; p = lp[6] * st.median([x for x in (ratio(z["curve"], lp[1]) for z in R["refs"] if z["rank"] == "500") if x])
    if p > rec: up.append(f"{n} {rec/1e4:.1f}万→{p/1e4:.1f}万")
print("above recorded 0:00 prediction:", up or "none")
