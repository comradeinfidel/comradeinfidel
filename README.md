<div align="center">

<img src="assets/pikatardio.png" alt="Pikatardio" width="180"/>

# ⚡ Pikatardio ⚡

*Your Pokémon Master AI — fun, playful, and 100% factual*

</div>

---

Pika pika! Meet **Pikatardio** — an AI agent with the heart of a Pikachu and the knowledge of every Pokémon Professor combined. She's wildly enthusiastic, speaks in Pokémon-style expressions, and is a master across all generations, games, competitive play, TCG, anime, and lore. Oh, and she's always 100% factual.

## What She Knows

- **All 1000+ Pokémon** — stats, types, moves, abilities, evolutions, regional forms, lore
- **All generations & games** — mainline, remakes, spin-offs, GO, TCG, anime, manga
- **Competitive play** — VGC, Smogon, team building, EV/IV training, breeding, calcs
- **General knowledge** — factual and helpful on any topic, Pokémon-twist included

## Web App (Mobile-Optimized GUI)

The web app gives you a full chat interface — dark Pokémon-themed UI, streaming responses, markdown formatting, and suggestion chips to get started fast. Works great on mobile.

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Set your API key**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

**3. Start the server**
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

**4. Open in your browser**
```
http://localhost:8000
```

On mobile, connect to your computer's local IP instead of `localhost` (e.g. `http://192.168.1.x:8000`).

> Drop your Pikatardio character image at `assets/pikatardio.png` to show her avatar throughout the UI.

## CLI Version

Prefer the terminal? Run Pikatardio directly from the command line:

```bash
python pikatardio.py
```

## Project Structure

```
├── app.py            # FastAPI web server with SSE streaming
├── pikatardio.py     # CLI chat agent
├── static/
│   └── index.html    # Mobile-optimized chat UI
├── assets/
│   └── pikatardio.png  # ← put her image here
└── requirements.txt
```

## Rules of the Gym

- Pikatardio is **always truthful** — no made-up stats, no fabricated lore
- If she doesn't know something, she says so honestly
- She keeps the energy high but the information accurate

---

<div align="center">

*Powered by the Anthropic Claude API* • *Gotta know 'em all!* ⚡

</div>
