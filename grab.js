// Run on discord.com (PC browser), in any channel of the border server.
// Opens each idol's channel in turn, reads the border posts that are on screen,
// and shows them as text to copy and paste into the border page ("取り込み").
(async () => {
  const G = "1433106113288470632";
  const CH = { "櫻木真乃": "1433110779913179307", "風野灯織": "1433110905750814740", "八宮めぐる": "1433110999371616417", "月岡恋鐘": "1433112444980428881", "田中摩美々": "1433112599297396908", "白瀬咲耶": "1433112660978696192", "三峰結華": "1433112697414881442", "幽谷霧子": "1433112748148916234", "小宮果穂": "1433112962377187529", "園田智代子": "1433113002281926716", "西城樹里": "1433113042996166767", "杜野凛世": "1433113085081550848", "有栖川夏葉": "1433113121593102426", "大崎甘奈": "1433113223921401866", "大崎甜花": "1433113266518884424", "桑山千雪": "1433113298601119794", "芹沢あさひ": "1433113533863952557", "黛冬優子": "1433113574108168374", "和泉愛依": "1433113635475161260", "浅倉透": "1433113814689382480", "樋口円香": "1433113849082675342", "福丸小糸": "1433113915910393877", "市川雛菜": "1433113952446840973", "七草にちか": "1433114032696590376", "緋田美琴": "1433114090397761606", "斑鳩ルカ": "1433114296782422116", "鈴木羽那": "1433114329175294026", "郁田はるき": "1433114365548167272" };
  const RANKS = ["1", "12", "50", "100", "500"];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const parse = t => {
    const s = { vals: {} }; let pend = null;
    for (const raw of t.split("\n")) {
      const l = raw.trim(); if (!l) continue; let m;
      if (!s.title && (m = l.match(/^(.+ライブイベント)\s*[\(（](.+)[\)）]\s*$/))) { s.title = m[1].trim(); s.idol = m[2].trim(); continue; }
      if ((m = l.match(/開催期間[:：]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*[~〜]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})/))) { s.start = m[1]; s.end = m[2]; continue; }
      if ((m = l.match(/現在時刻[:：]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*[\(（]経過率\s*([\d.]+)%[\)）]/))) { s.now = m[1]; s.pct = +m[2]; continue; }
      if ((m = l.match(/^(?:🥇|🥈|🥉)?\s*(\d+)位\s*-/))) { pend = m[1]; continue; }
      if (l.includes("ランク - ")) { pend = null; continue; }
      if ((m = l.match(/^([^:：\d]{1,12})[:：]\s*([\d,]+)/)) && pend != null) { s.vals[pend] = +m[2].replace(/,/g, ""); pend = null; }
    }
    return s.start && s.now && Object.keys(s.vals).length ? s : null;
  };
  const key = (a, b) => [a, b].map(x => x.replace(/[-:]/g, "").replace(" ", "-")).join("_");

  document.getElementById("sb-grab")?.remove();
  const box = document.createElement("div");
  box.id = "sb-grab";
  box.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:999999;width:360px;background:#fff;color:#002841;font:14px/1.6 sans-serif;padding:14px;border:1px solid #9cc;box-shadow:0 6px 24px rgba(0,0,0,.3)";
  box.innerHTML = '<b>ボーダー取り込み</b><div id="sb-msg" style="margin:6px 0">読み込み中…</div>'
    + '<textarea id="sb-out" readonly style="width:100%;height:90px;font:11px monospace;display:none"></textarea>'
    + '<div style="display:flex;gap:8px;margin-top:8px"><button id="sb-copy" style="display:none;flex:1;padding:6px">コピー</button><button id="sb-close" style="padding:6px">閉じる</button></div>';
  document.body.appendChild(box);
  const msg = box.querySelector("#sb-msg"), out = box.querySelector("#sb-out"), copy = box.querySelector("#sb-copy");
  box.querySelector("#sb-close").onclick = () => box.remove();

  const back = location.pathname, points = {}; let n = 0, i = 0;
  for (const [name, id] of Object.entries(CH)) {
    msg.textContent = `${++i}/28 ${name}`;
    history.pushState({}, "", `/channels/${G}/${id}`); dispatchEvent(new PopStateEvent("popstate"));
    const sel = `li[id^="chat-messages-${id}-"]`;
    for (let k = 0; k < 30 && !document.querySelector(sel); k++) await sleep(300);
    await sleep(900);
    for (const li of document.querySelectorAll(sel)) {
      const s = parse(li.innerText); if (!s || new Date(s.end.replace(" ", "T") + ":00+09:00") < Date.now()) continue;
      const ev = points[key(s.start, s.end)] ??= { title: s.title || "ライブイベント", start: s.start, end: s.end, idols: {} };
      const rows = ev.idols[s.idol || name] ??= [];
      if (rows.some(r => r[0] === s.now)) continue;
      rows.push([s.now, s.pct, ...RANKS.map(r => s.vals[r] ?? null)]); n++;
    }
  }
  history.pushState({}, "", back); dispatchEvent(new PopStateEvent("popstate"));
  out.value = JSON.stringify(points);
  out.style.display = copy.style.display = "block";
  msg.textContent = n ? `${n}件読めました。コピーして、ボーダー速報の「取り込み」に貼ってください。` : "ボーダーの投稿が見つかりませんでした。シャニソンボーダーのサーバーを開いてから使ってください。";
  copy.onclick = async () => {
    out.select();
    try { await navigator.clipboard.writeText(out.value); } catch (e) { document.execCommand("copy"); }
    copy.textContent = "コピーしました";
  };
})();
