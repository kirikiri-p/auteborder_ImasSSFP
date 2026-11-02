// Paste into the in-app browser (javascript_tool) on discord.com, once per page load.
// Then: window.__pts = {}; await __grabAt(0, 7) ... (7 channels per call stays under the 45 s limit),
// and finally __export("2026-11-02 14:28") returns compact lines "name|HHMM,1,12,50,100,500,10,SS;..."
// for posts after that time, plus a gap/pct check. Save them to a file and run tools/merge_export.py.
// Pass a time (ms) as the 3rd argument of __grabAt to read around a past moment (about 6 h either side).
window.__grabAt = async (from, to, tms) => {
  const G = "1433106113288470632";
  const CH = { "櫻木真乃": "1433110779913179307", "風野灯織": "1433110905750814740", "八宮めぐる": "1433110999371616417", "月岡恋鐘": "1433112444980428881", "田中摩美々": "1433112599297396908", "白瀬咲耶": "1433112660978696192", "三峰結華": "1433112697414881442", "幽谷霧子": "1433112748148916234", "小宮果穂": "1433112962377187529", "園田智代子": "1433113002281926716", "西城樹里": "1433113042996166767", "杜野凛世": "1433113085081550848", "有栖川夏葉": "1433113121593102426", "大崎甘奈": "1433113223921401866", "大崎甜花": "1433113266518884424", "桑山千雪": "1433113298601119794", "芹沢あさひ": "1433113533863952557", "黛冬優子": "1433113574108168374", "和泉愛依": "1433113635475161260", "浅倉透": "1433113814689382480", "樋口円香": "1433113849082675342", "福丸小糸": "1433113915910393877", "市川雛菜": "1433113952446840973", "七草にちか": "1433114032696590376", "緋田美琴": "1433114090397761606", "斑鳩ルカ": "1433114296782422116", "鈴木羽那": "1433114329175294026", "郁田はるき": "1433114365548167272" };
  const RANKS = ["1", "12", "50", "100", "500", "10", "SS"];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const parse = t => {
    const s = { vals: {} }; let pend = null;
    for (const raw of t.split("\n")) {
      const l = raw.trim(); if (!l) continue; let m;
      if (!s.title && (m = l.match(/^(.+ライブイベント)\s*[\(（](.+)[\)）]\s*$/))) { s.title = m[1].trim(); s.idol = m[2].trim(); continue; }
      if ((m = l.match(/開催期間[:：]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*[~〜]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})/))) { s.start = m[1]; s.end = m[2]; continue; }
      if ((m = l.match(/現在時刻[:：]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*[\(（]経過率\s*([\d.]+)%[\)）]/))) { s.now = m[1]; s.pct = +m[2]; continue; }
      if ((m = l.match(/^(?:🥇|🥈|🥉)?\s*(\d+)位\s*-/))) { pend = m[1]; continue; }
      if (l.includes("ランク - ")) { pend = l.startsWith("SSランク") ? "SS" : null; continue; }
      if ((m = l.match(/^([^:：\d]{1,12})[:：]\s*([\d,]+)/)) && pend != null) { s.vals[pend] = +m[2].replace(/,/g, ""); pend = null; }
    }
    return s.start && s.now && Object.keys(s.vals).length ? s : null;
  };
  window.__pts = window.__pts || {}; let n = 0;
  for (const [name, id] of Object.entries(CH).slice(from, to)) {
    const t = tms || Date.now(), snow = ((BigInt(t) - 1420070400000n) << 22n).toString();
    history.pushState({}, "", `/channels/${G}/${id}/${snow}`); dispatchEvent(new PopStateEvent("popstate"));
    const sel = `li[id^="chat-messages-${id}-"]`;
    const age = li => Math.abs(t - Number((BigInt(li.id.split("-").pop()) >> 22n) + 1420070400000n));
    for (let k = 0; k < 40 && ![...document.querySelectorAll(sel)].some(li => age(li) < 40 * 60000); k++) await sleep(250);
    await sleep(700);
    for (const li of document.querySelectorAll(sel)) {
      const s = parse(li.innerText); if (!s) continue;
      const rows = window.__pts[s.idol || name] ??= [];
      if (rows.some(r => r[0] === s.now)) continue;
      rows.push([s.now, s.pct, ...RANKS.map(r => s.vals[r] ?? null)]); n++;
    }
  }
  return n;
};
window.__export = after => {
  const S0 = new Date("2026-10-31T12:00:00+09:00").getTime(), E0 = new Date("2026-11-06T20:59:00+09:00").getTime();
  const ms = s => new Date(s.replace(" ", "T") + ":00+09:00").getTime();
  const lines = [], gaps = [], bad = [];
  for (const [k, v] of Object.entries(window.__pts)) {
    const r = v.filter(x => x[0] > after).sort((a, b) => a[0] < b[0] ? -1 : 1);
    let prev = ms(after);
    for (const x of r) { const t = ms(x[0]); if (Math.abs(Math.round((t - S0) / (E0 - S0) * 10000) / 100 - x[1]) > 0.005) bad.push(k + x[0]); if (t - prev > 20 * 60000) gaps.push(k + x[0]); prev = t; }
    lines.push(k + "|" + r.map(x => x[0].slice(5, 7) + x[0].slice(8, 10) + x[0].slice(11).replace(":", "") + "," + x.slice(2).join(",")).join(";"));
  }
  return { idols: lines.length, gaps, bad, last: [...new Set(Object.values(window.__pts).map(v => v.map(x => x[0]).sort().pop()))], data: lines.join("\n") };
};
"ok";
