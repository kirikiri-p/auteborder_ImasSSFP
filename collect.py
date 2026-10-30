#!/usr/bin/env python3
"""Collect border posts from your own Discord server with an official bot account.

Reads every text channel in GUILD_ID, picks up the border posts (plain text or
embeds), and writes:
  data/points.json   all snapshots, keyed by event and idol (for the border book)
  data/latest.txt    the newest post per idol, in the same text format as the
                     border bot (paste it into the border book as-is)
  data/state.json    the last message id read in each channel

Environment:
  DISCORD_TOKEN  bot token (keep it in GitHub Secrets)
  GUILD_ID       your server's id
  START_JST      optional, e.g. "2026-10-31 12:00"; first run reads from here
Standard library only.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://discord.com/api/v10"
JST = timezone(timedelta(hours=9))
DISCORD_EPOCH = 1420070400000
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
RANKS = ["1", "12", "50", "100", "500"]


# ---------------------------------------------------------------- Discord API
def api(path, token):
    req = urllib.request.Request(
        API + path,
        headers={
            "Authorization": "Bot " + token,
            "User-Agent": "DiscordBot (border-collector, 1.0)",
        },
    )
    for _ in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = float(json.loads(e.read().decode("utf-8")).get("retry_after", 2))
                time.sleep(wait + 0.5)
                continue
            raise
    raise RuntimeError("rate limited too many times: " + path)


def snowflake_from_jst(s):
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
    return str((int(dt.timestamp() * 1000) - DISCORD_EPOCH) << 22)


def fetch_after(channel_id, after, token):
    """All messages newer than `after`, oldest first."""
    out = []
    while True:
        batch = api(f"/channels/{channel_id}/messages?limit=100&after={after}", token)
        if not batch:
            break
        batch.sort(key=lambda m: int(m["id"]))
        out.extend(batch)
        after = batch[-1]["id"]
        if len(batch) < 100:
            break
    return out


# ---------------------------------------------------------------- parsing
def message_text(m):
    """Flatten content and embeds into lines, the way the post reads on screen."""
    parts = [m.get("content") or ""]
    for e in m.get("embeds") or []:
        for k in ("title", "description"):
            if e.get(k):
                parts.append(e[k])
        for f in e.get("fields") or []:
            parts.append(f"{f.get('name', '')}\n{f.get('value', '')}")
        if (e.get("footer") or {}).get("text"):
            parts.append(e["footer"]["text"])
    text = "\n".join(p for p in parts if p)
    return re.sub(r"[*_`]", "", text)  # drop markdown emphasis


RE_TITLE = re.compile(r"^(.+ライブイベント)\s*[\(（](.+)[\)）]\s*$")
RE_PERIOD = re.compile(r"開催期間[:：]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*[~〜]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})")
RE_NOW = re.compile(r"現在時刻[:：]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*[\(（]経過率\s*([\d.]+)%[\)）]")
RE_RANK = re.compile(r"^(?:🥇|🥈|🥉)?\s*(\d+)位\s*-")
RE_VALUE = re.compile(r"^([^:：\d]{1,12})[:：]\s*([\d,]+)")


def parse(text, fallback_idol):
    """Return a snapshot dict, or None if this is not a border post."""
    snap = {"title": None, "idol": None, "start": None, "end": None,
            "now": None, "pct": None, "vals": {}, "label": None}
    pending = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = RE_TITLE.match(line)
        if m and not snap["title"]:
            snap["title"], snap["idol"] = m.group(1).strip(), m.group(2).strip()
            continue
        m = RE_PERIOD.search(line)
        if m:
            snap["start"], snap["end"] = m.group(1), m.group(2)
            continue
        m = RE_NOW.search(line)
        if m:
            snap["now"], snap["pct"] = m.group(1), float(m.group(2))
            continue
        m = RE_RANK.match(line)
        if m:
            pending = m.group(1)
            continue
        if "ランク - " in line:
            pending = None
            continue
        m = RE_VALUE.match(line)
        if m and pending is not None:
            snap["vals"][pending] = int(m.group(2).replace(",", ""))
            snap["label"] = snap["label"] or m.group(1).strip()
            pending = None
    if not (snap["start"] and snap["now"] and snap["vals"]):
        return None
    snap["idol"] = snap["idol"] or fallback_idol
    snap["title"] = snap["title"] or "ライブイベント"
    return snap


def event_key(start, end):
    f = lambda s: s.replace("-", "").replace(":", "").replace(" ", "-")
    return f"{f(start)}_{f(end)}"


def to_point(s):
    return [s["now"], s["pct"]] + [s["vals"].get(r) for r in RANKS]


def to_bot_text(ev, idol, p):
    """Rebuild a post the border book's parser reads."""
    lines = [f"{ev['title']} ({idol})",
             f"📅 開催期間: {ev['start']} ~ {ev['end']}",
             f"現在時刻: {p[0]} (経過率 {p[1]:.2f}%)"]
    for r, v in zip(RANKS, p[2:]):
        if v is not None:
            lines += [f"{r}位 - (記録)", f"観客動員数: {v:,}"]
    return "\n".join(lines)


# ---------------------------------------------------------------- storage
def load(name, default):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def merge(points, snap):
    """Add one snapshot; return True if it was new."""
    key = event_key(snap["start"], snap["end"])
    ev = points.setdefault(key, {"title": snap["title"], "start": snap["start"],
                                 "end": snap["end"], "idols": {}})
    rows = ev["idols"].setdefault(snap["idol"], [])
    p = to_point(snap)
    for i, q in enumerate(rows):
        if q[0] == p[0]:
            rows[i] = p
            return False
    rows.append(p)
    rows.sort(key=lambda q: (q[1], q[0]))
    return True


def write_latest(points):
    blocks = []
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    for key, ev in sorted(points.items()):
        if ev["end"] < now:
            continue  # only events still running
        for idol, rows in sorted(ev["idols"].items()):
            if rows:
                blocks.append(to_bot_text(ev, idol, rows[-1]))
    with open(os.path.join(DATA, "latest.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks) + ("\n" if blocks else ""))


# ---------------------------------------------------------------- main
def main():
    token = os.environ["DISCORD_TOKEN"]
    guild = os.environ["GUILD_ID"]
    start = os.environ.get("START_JST") or datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    state = load("state.json", {})
    points = load("points.json", {})
    labels = set()
    added = empty = 0
    raw_latest = {}

    all_channels = api(f"/guilds/{guild}/channels", token)
    kinds = {0: "text", 2: "voice", 4: "category", 5: "news", 13: "stage", 15: "forum", 16: "media"}
    print("visible channels: " + ", ".join(
        f"#{c.get('name')}({kinds.get(c.get('type'), c.get('type'))})" for c in all_channels))
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "channels.txt"), "w", encoding="utf-8") as f:
        for c in sorted(all_channels, key=lambda c: (c.get("parent_id") or "", c.get("position", 0))):
            f.write(f"{c['id']}\t{kinds.get(c.get('type'), c.get('type'))}\t{c.get('name')}\tparent={c.get('parent_id')}\n")
    channels = [c for c in all_channels if c.get("type") in (0, 5)]
    for ch in channels:
        cid = ch["id"]
        try:
            msgs = fetch_after(cid, state.get(cid, snowflake_from_jst(start)), token)
            # The newest message again, in case the bot edits one post in place.
            msgs += api(f"/channels/{cid}/messages?limit=1", token)
        except urllib.error.HTTPError as e:
            print(f"skip #{ch.get('name')}: HTTP {e.code}", file=sys.stderr)
            continue
        if msgs:
            newest = max(msgs, key=lambda m: int(m["id"]))
            raw_latest[ch.get("name", cid)] = {
                "id": newest["id"],
                "timestamp": newest.get("timestamp"), "edited": newest.get("edited_timestamp"),
                "content": newest.get("content"), "embeds": newest.get("embeds"),
                "attachments": [a.get("filename") for a in newest.get("attachments") or []],
            }
        for m in msgs:
            text = message_text(m)
            if not text.strip() and not m.get("attachments"):
                empty += 1
            s = parse(text, ch.get("name", cid))
            if s:
                added += merge(points, s)
                labels.add(s["label"])
        if msgs:
            state[cid] = max([state.get(cid, "0")] + [m["id"] for m in msgs], key=int)

    save("state.json", state)
    save("points.json", points)
    save("raw_latest.json", raw_latest)  # newest raw message per channel, for checking the format
    write_latest(points)
    print(f"channels={len(channels)} new_snapshots={added} labels={sorted(l for l in labels if l)}")
    if empty:
        print(f"warning: {empty} messages had no text; is Message Content Intent on?", file=sys.stderr)


if __name__ == "__main__":
    main()
