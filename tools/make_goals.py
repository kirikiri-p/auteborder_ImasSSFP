# Usage: python3 make_goals.py "2026-11-01 23:58" 1.2
# Records, for the 20 idols aimed at 500th, the site's prediction (median of past ratios) at that post x factor.
import json, statistics as st, sys
t, k = sys.argv[1], float(sys.argv[2])
R = json.load(open('data/reference.json')); P = json.load(open('data/points.json'))['20261031-1200_20261106-2059']['idols']
T = ['幽谷霧子','和泉愛依','小宮果穂','大崎甘奈','八宮めぐる','市川雛菜','緋田美琴','郁田はるき']
def ratio(c, p):
    if p < c[0][0]: return None
    for i in range(1, len(c)):
        if c[i][0] >= p:
            a, b = c[i-1], c[i]; return a[1] + (b[1]-a[1])*(p-a[0])/(b[0]-a[0]) if b[0] > a[0] else b[1]
    return 1
goals, preds = {}, {}
for n, rows in P.items():
    if n in T: continue
    x = [r for r in rows if r[0] == t]; assert x, (n, t); x = x[0]
    rs = [v for v in (ratio(z['curve'], x[1]) for z in R['refs'] if z['rank'] == '500') if v]
    preds[n] = round(x[6] * st.median(rs)); goals[n] = round(preds[n] * k)
json.dump({"rank": "500", "note": f"{t[5:].replace('-', '/')}の予測×{k}", "at": t, "factor": k, "pred": preds, "goals": goals},
          open('data/goals.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for n in sorted(goals, key=lambda n: -goals[n]): print(n, preds[n], goals[n])
