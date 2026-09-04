# 𝐉ᴏʜɴ 𝐖ɪᴄᴋ.་༘࿐ ᯓ 𝐌⃝ᴀнσɾαgᴀ ⋆ཋྀ🪽𓆪 — GC Controller Bot

Everything is hardcoded in `bot.py` (API_ID, API_HASH, BOT_TOKEN, OWNER_ID). Just deploy.

## Deploy on Render (free)
1. Push this folder to a GitHub repo.
2. Render → New → **Web Service** → connect the repo.
   - Runtime: Python · Build: `pip install -r requirements.txt` · Start: `python bot.py`
   - (or just let Render pick up `render.yaml`)
3. Deploy. Your URL: `https://<name>.onrender.com` → shows "controller online ✅".
4. **Persist sessions** (recommended): Render → Disks → add a disk, mount path `/data`,
   then add env var `DATA_DIR=/data`. Without it, logins are lost on every redeploy.

## Keep it awake — UptimeRobot
UptimeRobot → New Monitor → HTTP(s) → URL `https://<name>.onrender.com/health` → interval 5 min.

## Usage
Send `/start` to the bot from the owner account (5206554804). Everything is available via inline buttons:
Login · Status · GC Maker · Manage GC · Broadcast · Folders · Access · Help.
Text commands (`.kick`, `.cmd on`, `.auth` …) also work — see `/help`.
