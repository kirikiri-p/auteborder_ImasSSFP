"""Merge border exports and/or my fan counts into data/, then rebuild data/latest.txt.

  python3 tools/merge_export.py --borders exp.txt          # lines from __export(): name|MMDDHHMM,1,12,50,100,500,10,SS;...
  python3 tools/merge_export.py --my "2026-11-02 14:37" scores.json   # {"幽谷霧子": 2342960, ...} (all 28)
Prints what changed, resets the goals by goals.json "plan" (prediction x 90% margin, see tools/model.py), the goals
still open and idols whose 500th prediction is now above the last 0:00 record (pred500). Commit and push afterwards.
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
G = json.load(open("data/goals.json", encoding="utf-8"))
import model   # tools/model.py: mixed prediction (level x this event's 24 h pace) and the 90% margins
# Goals (goals.json "plan"): goal = prediction now x m90(rank, plan.margin_at %) -- the 90% margin of the last hours,
# since the prediction itself is redone on every update. "reserve" = prediction x m90 at the elapsed % now (worst case).
# Before plan.lock_from (the last day) a goal follows the prediction up and down; from then on it is never lowered.
plan = G["plan"]; G.setdefault("goals100", {}); G["now"] = {}
prev = {k: dict(G.get(k, {})) for k in ("goals", "goals100")}
changed = []
for n in ev:
    rk = "100" if n in plan["top100"] else "500"
    p, lp = model.pred(ev[n], rk)
    if p is None: continue
    mg = plan["factor"] if plan.get("factor") else model.margin(rk, plan.get("margin_at", lp[1])); g = round(p * mg); key = "goals100" if rk == "100" else "goals"   # plan.factor: fixed multiplier (11/4 19:40~: x1.2)
    old = G[key].get(n)
    if lp[0] >= plan["lock_from"] and old and G.get("locked", {}).get(n) and old > g: g = old
    if lp[0] >= plan["lock_from"]: G.setdefault("locked", {})[n] = True
    G[key][n] = g; G["now"][n] = {"rank": rk, "pred": round(p), "margin": round(mg, 3), "reserve": round(p * model.margin(rk, lp[1])), "at": lp[0]}
    if old and abs(g - old) >= 5000: changed.append(f"{n} {old/1e4:.1f}万→{g/1e4:.1f}万")
# Safe lines (model.safe_line): only come down as the end nears; "broken" = it had to go up this time
G["safe"] = {}; broken = []
for n in ev:
    for rk in ("1", "10", "50", "100", "500"):
        v, br = model.safe_line(ev[n], rk)
        if v: G["safe"].setdefault(n, {})[rk] = v
        if br and rk in ("100", "500") and (rk == "100") == (n in plan["top100"]): broken.append(f"{n} {rk}位")
if plan.get("goal") == "safe":   # 11/5 21:10~: goal = the safe line itself, always (11/6 1:43~ also after plan.lock_from)
    changed = []
    for n in ev:
        if n not in G["now"]: continue
        rk = G["now"][n]["rank"]; key = "goals100" if rk == "100" else "goals"; g = G["safe"].get(n, {}).get(rk)
        if not g: continue
        old = prev[key].get(n)
        G[key][n] = g; G["now"][n]["margin"] = round(g / G["now"][n]["pred"], 3)
        if old and abs(g - old) >= 5000: changed.append(f"{n} {old/1e4:.1f}万→{g/1e4:.1f}万")
open("data/goals.json", "w", encoding="utf-8").write(json.dumps(G, ensure_ascii=False, indent=1) + "\n")
print("safe line went up (prediction ran past the past events):", broken or "none")
print("goals changed:", changed or "none")
for n in plan["top100"]:
    g = G["goals100"][n]; d = G["now"][n]
    print(f"100th {n}: pred {d['pred']/1e4:.1f}万 x{d['margin']} = goal {g/1e4:.1f}万, now {my[n]/1e4:.1f}万, " + (f"あと{(g-my[n])/1e4:.1f}万" if my[n] < g else "reached") + f" (worst case now {d['reserve']/1e4:.0f}万)")
left = {n: g - my[n] for n, g in G["goals"].items() if g > my[n] and n not in plan["top100"]}
print("500 goals open: %.1f万" % (sum(left.values()) / 1e4), {n: round(v / 1e4, 1) for n, v in sorted(left.items(), key=lambda x: -x[1])})
up = [f"{n} {rec/1e4:.1f}万→{G['now'][n]['pred']/1e4:.1f}万" for n, rec in G.get("pred500", {}).items()
      if n not in plan["top100"] and n in G["now"] and G["now"][n]["pred"] > rec]
print("500th prediction above the last 0:00 record:", up or "none")
