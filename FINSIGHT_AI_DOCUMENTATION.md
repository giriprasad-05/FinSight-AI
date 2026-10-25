# FinSight AI — Complete Architecture, Code & API Documentation

> **FinSight AI** is a full-stack, institutional-grade financial analytics and explainable AI system combining real-time market data, XGBoost machine learning directional forecasting, multi-factor risk modeling, and a private local LLM assistant (via LM Studio).

---

## 1. System Architecture Overview

FinSight AI is built as a **3-Tier Microservice Architecture**:

```
+-----------------------------------------------------------------------------------+
|                                 FRONTEND LAYER                                    |
|                        React 19 + Vite + TypeScript                               |
|                          http://localhost:5173/                                   |
+-----------------------------------------------------------------------------------+
                                         |
                            (REST Requests / JSON API)
                                         v
+-----------------------------------------------------------------------------------+
|                              BACKEND GATEWAY LAYER                                |
|                        Node.js + Express (Port 5000)                              |
|   - Authentication (scrypt + HMAC-SHA256 Tokens)  - Rate Limiting & Helmet       |
|   - Route Protection                              - Proxy to ML Engine            |
+-----------------------------------------------------------------------------------+
                                         |
                            (Internal Proxy / Axios)
                                         v
+-----------------------------------------------------------------------------------+
|                            MACHINE LEARNING ENGINE                                |
|                        Python 3.13 + FastAPI (Port 8000)                          |
|   - XGBoost Directional Model v2                  - Technical Indicator Engine    |
|   - Institutional Risk Classifier                 - Local LLM Integrator          |
+-----------------------------------------------------------------------------------+
                   |                                             |
         (Yahoo Finance API)                          (OpenAI-Compatible REST API)
                   v                                             v
     +---------------------------+                 +---------------------------+
     |   External Market Data    |                 |   Local LM Studio Model   |
     |   Live Prices & OHLCV     |                 |  http://localhost:1234/v1 |
     +---------------------------+                 +---------------------------+
```

---

## 2. Directory Structure & Key Files

```
FinSight AI/
├── scripts/
│   └── dev.js                    # Cross-platform multi-service launcher script
├── backend/                      # Node.js API Gateway
│   ├── src/
│   │   ├── app.js                # Express application setup, CORS, Helmet, Rate Limiter
│   │   ├── server.js             # HTTP server entry point (Port 5000)
│   │   ├── services/
│   │   │   ├── authService.js    # Password hashing (scrypt) & HMAC JWT token generation
│   │   │   ├── mlService.js      # Proxy wrapper to Python FastAPI ML service
│   │   │   └── llmService.js     # LM Studio model auto-discovery & chat builder
│   │   ├── controllers/
│   │   │   ├── authController.js # Login, Signup, Logout, GetMe endpoints
│   │   │   └── chatController.js # AI Mentor chat request handler
│   │   ├── middleware/
│   │   │   └── authMiddleware.js # Bearer token verification guard
│   │   └── routes/
│   │       ├── authRoutes.js     # /api/auth endpoints
│   │       └── stockRoutes.js    # /api/stocks endpoints
│   └── data/
│       └── users.json            # Persistent user credentials database (hashed passwords)
├── ml-service/                   # Python FastAPI ML Microservice
│   ├── main.py                   # FastAPI application server (Port 8000)
│   ├── models/
│   │   └── xgboost_trend_model_v2.json # Trained XGBoost trend classifier
│   └── src/
│       ├── data_fetcher.py       # Yahoo Finance market data retreival
│       ├── features.py           # Technical indicator feature engineering (RSI, MACD, SMA)
│       ├── predict.py            # Model inference & probability calculations
│       ├── risk.py               # Volatility, Beta, and Max Drawdown evaluation
│       ├── ai_explainer.py       # Deterministic XAI explanation builder
│       └── local_llm.py          # LM Studio connection, prompt guardrails & JSON parser
└── Frontend/                     # React Single Page Application
    ├── src/
    │   ├── App.tsx               # Main React router & layout wrapper
    │   ├── components/
    │   │   ├── auth/ProtectedRoute.tsx  # Auth guard component
    │   │   ├── layout/Navbar.tsx        # Taskbar with auth state, about & dashboard links
    │   │   └── search/StockSearch.tsx   # Live stock search bar
    │   ├── store/
    │   │   ├── authStore.ts      # Zustand store for user session & tokens
    │   │   └── stockStore.ts     # Zustand store for active ticker & timeframes
    │   ├── pages/
    │   │   ├── auth/LoginPage.tsx       # Dual Tab Sign In / Sign Up page
    │   │   ├── About/AboutPage.tsx      # System architecture & capabilities page
    │   │   └── stock/StockDashboard.tsx # Main stock research dashboard
    │   └── services/
    │       ├── apiService.ts     # Central fetch client attaching Bearer tokens
    │       └── authService.ts    # Frontend auth API bindings
    └── vite.config.ts            # Vite dev server configuration & /api proxy
```

---

## 3. Deep Dive: Authentication & Security System

* **Password Security:** Passwords are **never** stored in plain text. Passwords are hashed using Node's native `crypto.scryptSync(password, salt, 64)` with a 16-byte cryptographically secure random salt (`crypto.randomBytes(16)`).
* **Constant-Time Matching:** Verification uses `crypto.timingSafeEqual` to eliminate timing side-channel attacks.
* **Token Architecture:** Sessions are managed using **HMAC-SHA256 signed JWT tokens** (`base64Url(header).base64Url(payload).signature`).
* **Session Lifetime:** Tokens expire after 24 hours ($86,400$ seconds) and can be immediately revoked on server-side logout.

---

## 4. Deep Dive: Local Model API (LM Studio Integration)

The **Local Model API** allows FinSight AI to generate natural language explanations and power the interactive **Investment Mentor** using on-premise AI models running via LM Studio (or Ollama/LocalAI) on `http://localhost:1234/v1`.

### A. How Model Auto-Discovery Works (`GET /v1/models`)
Instead of hardcoding a specific model name, both Python (`local_llm.py`) and Node (`llmService.js`) query the local server's `/v1/models` endpoint:
1. Probe `http://localhost:1234/v1/models` with a 3-second timeout.
2. Filter out embedding models (e.g. models containing `embed` in their ID).
3. Automatically select the primary active loaded text-generation model.

### B. System Prompt Guardrails & Safety Constraints
To prevent hallucinated data or illegal financial advice, the system prompt enforces strict rules:
* **Authoritative Quantitative Data:** The LLM is explicitly forbidden from altering numerical prediction confidence, risk scores, or indicator values generated by XGBoost.
* **No Financial Advice:** The LLM is prohibited from telling users to "buy", "sell", or "hold" securities.
* **Structured Output Enforcement:** Returns strictly formatted JSON (`headline`, `summary`, `drivers`, `risk_summary`, `watch_items`).

### C. Token-Efficient Context Construction
Raw candle chart data (e.g., 500 daily OHLCV rows) contains thousands of tokens that waste memory and slow down local inference. FinSight AI extracts a **compact financial payload** containing only:
* Current price and price change percentage.
* XGBoost prediction direction (`UP`, `DOWN`, `FLAT`) and confidence %.
* Risk score ($0 - 100$), risk level (`Low`, `Medium`, `High`, `Very High`), volatility, and max drawdown.
* Primary driver features (RSI 14, 5-day return, SMA 20/50 delta, MACD).

### D. Zero-Downtime Fallback Architecture
If LM Studio is offline, unreachable, or times out ($>15$ seconds):
1. The system catches the network timeout/connection exception.
2. It seamlessly falls back to the **Deterministic Explanation Engine** (`ai_explainer.py`).
3. The dashboard continues working 100% without throwing errors or crashing.

---

## 5. Complete API Reference

### A. Node.js Backend Gateway Endpoints (`http://localhost:5000`)

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | No | Returns Node backend status & Python ML service status. |
| `POST` | `/api/auth/signup` | No | Creates a new user account and returns signed token. |
| `POST` | `/api/auth/login` | No | Authenticates username/email + password and returns token. |
| `POST` | `/api/auth/logout` | Yes | Revokes active Bearer token. |
| `GET` | `/api/auth/me` | Yes | Returns current authenticated user profile. |
| `GET` | `/api/stocks/:ticker` | No | Returns combined stock profile and quote. |
| `GET` | `/api/stocks/:ticker/quote` | No | Returns live quote & market status from Python ML service. |
| `GET` | `/api/stocks/:ticker/history` | No | Returns historical OHLCV chart points (`1D`, `1W`, `1M`, `3M`, `1Y`, `5Y`). |
| `GET` | `/api/predictions/:ticker` | No | Returns XGBoost trend prediction direction and probabilities. |
| `GET` | `/api/risk/:ticker` | No | Returns quantitative multi-factor risk assessment. |
| `GET` | `/api/analysis/:ticker` | No | Returns combined trend, risk, and XAI diagnostic payload. |
| `POST` | `/api/chat` | No/Optional | Connects user chat messages to local LM Studio via `llmService.js`. |

---

### B. Python FastAPI Microservice Endpoints (`http://127.0.0.1:8000`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Returns FastAPI status, loaded model version (`xgboost_trend_model_v2.json`), and library versions. |
| `GET` | `/quote/{ticker}` | Fetches live quote & company info from Yahoo Finance. |
| `GET` | `/predict/{ticker}` | Runs XGBoost ML prediction for stock trend direction (`UP`, `DOWN`, `FLAT`). |
| `GET` | `/risk/{ticker}` | Calculates annualized volatility, beta, max drawdown, and risk classification. |
| `GET` | `/analysis/{ticker}` | Returns aggregated quote, indicator features, trend prediction, and risk metrics. |
| `POST` | `/chat` | Proxies user chat prompt and stock context to local LLM server. |

---

### C. Local LLM Server Endpoints (LM Studio — `http://localhost:1234/v1`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/v1/models` | OpenAI-compatible endpoint used for model auto-discovery. |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat completions endpoint generating streaming or structured JSON explanations. |

---

### D. External Market Data API (Yahoo Finance)

| Source | Integration Library | Purpose |
| :--- | :--- | :--- |
| Yahoo Finance API | `yfinance` (Python) | High-frequency stock quotes, company metadata, and historical price bars. |

---

## 6. How to Run the Project

1. Start all 3 microservices concurrently from the root directory:
   ```bash
   npm run dev
   ```
2. Open your browser to:
   * **Frontend Application:** `http://localhost:5173/`
   * **Node Backend Health:** `http://localhost:5000/api/health`
   * **Python ML Service Docs:** `http://127.0.0.1:8000/docs`
