# border-collector

Reads the border posts in your own Discord server every 15 minutes (GitHub Actions) and saves them in `data/`.

- `data/latest.txt` — newest post per idol, in the border bot's text format. Paste it into the border book as-is.
- `data/points.json` — every snapshot: `{event key: {title, start, end, idols: {name: [[time, elapsed %, 1st, 12th, 50th, 100th, 500th], ...]}}}`.
- `data/state.json` — last message id read per channel.

## Setup

1. Discord Developer Portal → New Application → **Bot**: reset and copy the token; turn on **Message Content Intent**.
2. **OAuth2 → URL Generator**: scope `bot`; permissions **View Channels** and **Read Message History**. Open the URL and add the bot to your server.
3. The server id is set in `.github/workflows/collect.yml` (`GUILD_ID`); it is not a secret.
4. In this repo: Settings → Secrets and variables → Actions → add `DISCORD_TOKEN`.
5. Actions tab → **collect borders** → **Run workflow** once, and check the log line `channels=… new_snapshots=…`.

Runs on a schedule can be late by several minutes or more when GitHub is busy.

## Site

`index.html` is served by GitHub Pages from `main` (root). It reads `data/points.json` and `data/reference.json`.

Idol pictures are optional: put `img/<full name>.png` (for example `img/幽谷霧子.png`, portrait, face near the top) and the card and the detail view will show it. Without a picture, the first character of the given name is shown in the unit color. Check the rights and the official rules for any picture you add; this repository and site are public.
