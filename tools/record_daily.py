# Usage: python3 tools/record_daily.py "2026-11-02 23:59" ["2026-11-01 23:59"]
# Records the site's prediction (tools/model.py: level x this event's 24 h pace) for every idol, 500th and 100th,
# under goals.json "daily"[time], and prints the idols whose prediction is above the one at the earlier post.
# Goals are left as they are; pred500 (the alert baseline) becomes this record.
import json, statistics as st, sys
t = sys.argv[1]; prev = sys.argv[2] if len(sys.argv) > 2 else None
R = json.load(open('data/reference.json')); P = json.load(open('data/points.json'))['20261031-1200_20261106-2059']['idols']
COL = {"100": 5, "500": 6}
def ratio(c, p):
    if p < c[0][0]: return None
    for i in range(1, len(c)):
        if c[i][0] >= p:
            a, b = c[i-1], c[i]; return a[1] + (b[1]-a[1])*(p-a[0])/(b[0]-a[0]) if b[0] > a[0] else b[1]
    return 1
sys.path.insert(0, "tools"); import model   # same mixed prediction as the site
def preds(at):
    out = {}
    for rk in COL:
        out[rk] = {}
        for n, rows in P.items():
            p, lp = model.pred(rows, rk, upto=at); assert p and lp[0] == at, (n, at)
            out[rk][n] = round(p)
    return out
G = json.load(open('data/goals.json', encoding='utf-8')); now = preds(t)
G.setdefault("daily", {})[t] = now
G["pred500"] = dict(now["500"])   # the site and merge_export flag a 500th prediction above this
open('data/goals.json', 'w', encoding='utf-8').write(json.dumps(G, ensure_ascii=False, indent=1) + "\n")
if prev:
    old = G["daily"].get(prev) or preds(prev)
    for rk in ("500", "100"):
        up = sorted(((now[rk][n] - old[rk][n], n) for n in now[rk] if now[rk][n] > old[rk][n]), reverse=True)
        print(rk, "up:", [f"{n} {old[rk][n]/1e4:.1f}万→{now[rk][n]/1e4:.1f}万" for d, n in up] or "none")
