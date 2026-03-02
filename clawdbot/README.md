# ClawdBot

> *The golden eyes are always watching.*

A Discord bot with an anime aesthetic and a sharp personality. ClawdBot is calm, perceptive, and just a little intimidating — but fiercely loyal to its server.

---

## Features

- **General Commands** — `!help`, `!ping`, `!clawd`, `!8ball`, `!roll`
- **Moderation** — `!kick`, `!ban`, `!unban`, `!purge`, `!slowmode`
- Extensible cog-based architecture for adding new features easily

---

## Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/comradeinfidel/comradeinfidel
cd comradeinfidel/clawdbot
pip install -r requirements.txt
```

### 2. Configure your bot token

```bash
cp .env.example .env
# Edit .env and add your Discord bot token
```

### 3. Add your avatar

Place your bot's face image at `assets/avatar.png`.

### 4. Run ClawdBot

```bash
python bot.py
```

---

## Commands

| Command | Description |
|---|---|
| `!help` | Show all commands |
| `!ping` | Check bot latency |
| `!clawd` | Get a response from Clawd |
| `!8ball <question>` | Ask the oracle |
| `!roll <NdN>` | Roll dice (e.g. `2d6`) |
| `!kick <user>` | Kick a member (requires permission) |
| `!ban <user>` | Ban a member (requires permission) |
| `!unban <username>` | Unban a user (requires permission) |
| `!purge <n>` | Delete N messages (requires permission) |
| `!slowmode <s>` | Set channel slowmode in seconds (requires permission) |

---

## Project Structure

```
clawdbot/
├── bot.py              # Entry point
├── requirements.txt
├── .env.example
├── assets/
│   └── avatar.png      # Bot face/avatar
└── cogs/
    ├── general.py      # General commands
    └── mod.py          # Moderation commands
```

---

*Made for @comradeinfidel*
