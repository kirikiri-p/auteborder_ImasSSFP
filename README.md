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
