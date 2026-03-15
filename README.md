# AI Personal Assistant

A Claude-powered mobile personal assistant that can do **literally anything online** — search the web, trade stocks & crypto, send payments, and more. Built with a Python FastAPI backend and React Native mobile app.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────┐
│         React Native App (Expo)        │
│  Chat UI • Portfolio • Settings        │
└────────────┬───────────────────────────┘
             │ WebSocket (real-time streaming)
┌────────────▼───────────────────────────┐
│         FastAPI Backend                │
│         Python + Anthropic SDK         │
└────────────┬───────────────────────────┘
             │
    ┌────────┴────────┐
    │  Claude Opus 4.6│  ◄── Adaptive Thinking
    │  with Tools     │
    └────────┬────────┘
             │
    ┌────────┴──────────────────────────────┐
    │              Tool Suite               │
    ├──────────┬──────────┬────────┬────────┤
    │ Web Search│ Payments │ Stocks │ Crypto │
    │ Web Fetch │  Stripe  │Alpaca  │Coinbase│
    └──────────┴──────────┴────────┴────────┘
```

---

## 🚀 Features

| Category | Capability |
|----------|-----------|
| 🔍 Web | Search the web, fetch any URL, summarize pages |
| 📈 Stocks | Get quotes, buy/sell shares, view portfolio (Alpaca) |
| ₿ Crypto | Get prices, buy/sell crypto, view balances (Coinbase) |
| 💳 Payments | Send payments, check status, view history (Stripe) |
| 🧠 AI | Claude Opus 4.6 with adaptive thinking — it reasons before acting |
| 📱 Mobile | Beautiful dark-themed React Native app for iOS & Android |
| ⚡ Streaming | Real-time streaming via WebSocket with tool event updates |

---

## 🛠️ Setup

### 1. Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys (see API Keys section below)

# Start the server
python main.py
```

The backend runs on `http://localhost:8000`.

### 2. Mobile App

```bash
cd mobile

# Install dependencies
npm install

# Start Expo
npx expo start

# Scan QR code with Expo Go app (iOS/Android)
# Or press 'i' for iOS Simulator, 'a' for Android Emulator
```

---

## 🔑 API Keys

### Anthropic (Required)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Add to `backend/.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### Alpaca — Stock Trading (Free)
1. Sign up at [alpaca.markets](https://alpaca.markets)
2. Get free paper trading API keys
3. Add to `backend/.env`:
   ```
   ALPACA_API_KEY=your_key
   ALPACA_SECRET_KEY=your_secret
   ALPACA_BASE_URL=https://paper-api.alpaca.markets  # paper trading
   # For live: ALPACA_BASE_URL=https://api.alpaca.markets
   ```

### Coinbase Advanced Trade — Crypto Trading
1. Go to [Coinbase Developer Platform](https://docs.cdp.coinbase.com/advanced-trade/docs/rest-api-auth)
2. Create API key with trading permissions
3. Add to `backend/.env`:
   ```
   COINBASE_API_KEY=organizations/.../apiKeys/...
   COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\n...
   ```

### Stripe — Payments
1. Sign up at [stripe.com](https://stripe.com)
2. Get test API keys from dashboard
3. Add to `backend/.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   ```

---

## 💬 Example Conversations

```
You: What's the current price of Bitcoin and Ethereum?

AI: [searches Coinbase]
    Bitcoin (BTC-USD): $98,432.00 (+2.3% 24h)
    Ethereum (ETH-USD): $3,847.00 (+1.8% 24h)

---

You: Buy $50 worth of ETH

AI: I'll buy $50 of ETH at the current price of ~$3,847.
    This will get you approximately 0.013 ETH.
    Confirm? (yes/no)

You: yes

AI: ✅ Order placed! Bought $50 of ETH-USD.
    Order ID: abc123
    Status: Filled

---

You: Search for the latest news about NVDA stock

AI: [searches web] Here's what I found...

---

You: Buy 1 share of Apple stock

AI: Current AAPL price: $189.50
    I'll place a market order for 1 share of AAPL.
    Total cost: ~$189.50
    Confirm? (yes/no)
```

---

## 🏛️ Project Structure

```
.
├── backend/
│   ├── main.py           # FastAPI app with WebSocket
│   ├── agent.py          # Claude agent + tool orchestration
│   ├── tools/
│   │   ├── payments.py   # Stripe integration
│   │   ├── stocks.py     # Alpaca stock trading
│   │   └── crypto.py     # Coinbase crypto trading
│   ├── requirements.txt
│   └── .env.example
│
└── mobile/
    ├── App.tsx            # Navigation + tab bar
    ├── src/
    │   ├── screens/
    │   │   ├── ChatScreen.tsx      # Main AI chat interface
    │   │   ├── PortfolioScreen.tsx # Portfolio overview
    │   │   └── SettingsScreen.tsx  # API key config
    │   ├── components/
    │   │   ├── MessageBubble.tsx   # Chat message UI
    │   │   └── QuickActions.tsx    # One-tap shortcuts
    │   ├── services/api.ts         # WebSocket client
    │   └── theme/index.ts          # Design system
    ├── package.json
    └── app.json
```

---

## 🔒 Safety

- **Confirmation required** for all trades and payments over $100
- **Paper trading by default** for Alpaca (no real money at risk)
- **Stripe test mode** by default (no real money charged)
- **Adaptive AI thinking** — Claude reasons carefully before any financial action
- API keys stored server-side only, never in the mobile app

---

## 🚀 Deployment

To deploy the backend on a server:

```bash
# Install dependencies
pip install -r requirements.txt

# Run with gunicorn + uvicorn workers
gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Or with Docker (add your own Dockerfile)
```

Update `WS_URL` in `mobile/src/services/api.ts` to point to your server.

---

## 🛡️ Disclaimer

This software is for educational and personal use. Trading stocks and cryptocurrencies involves financial risk. The AI assistant can execute real trades — always review confirmations carefully. Start with paper trading (Alpaca) and Stripe test mode.
