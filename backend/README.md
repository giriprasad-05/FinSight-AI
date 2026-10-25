# FinSight AI — Node.js/Express Backend

API gateway that sits between the React frontend and the Python FastAPI ML microservice.

```
React Frontend (port 5173)
        ↓  HTTP
Node.js / Express Backend (port 5000)
        ↓  HTTP (Axios)
Python FastAPI ML Service (port 8000)
        ↓
XGBoost Trend Model v2 + Risk Assessment Engine
```

---

## Quick Start

### 1. Install dependencies

```bash
cd backend
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env if needed — defaults work for local development
```

Default `.env`:
```
PORT=5000
ML_SERVICE_URL=http://127.0.0.1:8000
ML_TIMEOUT_MS=30000
FRONTEND_URL=http://localhost:5173
NODE_ENV=development
```

### 3. Start the Python ML service (FastAPI)

```bash
cd ml-service
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start the Node backend

```bash
cd backend
npm run dev        # development (auto-restart on file changes)
# or
npm start          # production
```

---

## Endpoints

### Node.js Backend (port 5000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Node + ML service health check |
| GET | `/api/stocks/:ticker` | Stock identity (ticker, market, date) |
| GET | `/api/predictions/:ticker` | XGBoost v2 trend prediction |
| GET | `/api/risk/:ticker` | Quantitative risk assessment |
| GET | `/api/analysis/:ticker` | Combined trend + risk (single call) |

### Python ML Service (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | ML service health + library versions |
| GET | `/predict/{ticker}` | Trend prediction (DOWN/FLAT/UP) |
| GET | `/risk/{ticker}` | Risk score (0–100), level, components |
| GET | `/analysis/{ticker}` | Both engines, run concurrently |
| GET | `/docs` | Interactive FastAPI docs (Swagger UI) |

---

## Ticker Format

| Market | Format | Examples |
|--------|--------|---------|
| US stocks | `TICKER` | `AAPL`, `MSFT`, `NVDA`, `BRK-B` |
| Indian NSE | `TICKER.NS` | `RELIANCE.NS`, `TCS.NS`, `INFY.NS` |
| Indian BSE | `TICKER.BO` | `RELIANCE.BO` |

**Validation rules:** letters, digits, dots, hyphens only — max 20 characters.

---

## Example Responses

### GET /api/health

```json
{
  "status": "ok",
  "service": "FinSight AI Node Backend",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "ml_service": {
    "status": "ok",
    "service": "FinSight AI ML Service",
    "version": "2.0.0",
    "model": "xgboost_trend_model_v2.json",
    "xgboost_version": "2.0.3"
  }
}
```

### GET /api/analysis/AAPL

```json
{
  "ticker": "AAPL",
  "market": "US",
  "data_date": "2024-01-15",
  "trend": {
    "prediction": "UP",
    "prediction_code": 2,
    "confidence": 0.61,
    "probabilities": { "DOWN": 0.17, "FLAT": 0.22, "UP": 0.61 },
    "model_version": "v2"
  },
  "risk": {
    "risk_score": 39.1,
    "risk_level": "MEDIUM",
    "components": { "volatility": 35.0, "drawdown": 42.0, "downside": 38.0, "recent": 41.5 },
    "raw_metrics": { "annualized_volatility": 0.28, "max_drawdown": -0.18 },
    "explanations": ["Moderate historical volatility of 28%"]
  },
  "indicators": { "RSI_14": 58.3, "MA_20": 182.5, "MA_50": 178.1 }
}
```

### GET /api/analysis/INVALID@@

```json
{
  "error": "Invalid ticker format: \"INVALID@@\". Only letters, digits, dots, and hyphens are allowed (max 20 characters).",
  "status": 400
}
```

---

## Project Structure

```
backend/
├── src/
│   ├── routes/
│   │   ├── stockRoutes.js        GET /api/stocks/:ticker
│   │   ├── predictionRoutes.js   GET /api/predictions/:ticker
│   │   ├── riskRoutes.js         GET /api/risk/:ticker
│   │   └── analysisRoutes.js     GET /api/analysis/:ticker
│   │
│   ├── controllers/
│   │   ├── stockController.js
│   │   ├── predictionController.js
│   │   ├── riskController.js
│   │   └── analysisController.js
│   │
│   ├── services/
│   │   ├── mlService.js          Axios client for Python ML service
│   │   └── stockService.js       Business-logic wrapper
│   │
│   ├── middleware/
│   │   └── errorHandler.js       Centralised error + 404 handlers
│   │
│   ├── utils/
│   │   └── tickerValidator.js    Ticker validation (whitelist regex)
│   │
│   ├── app.js                    Express app factory (routes, middleware)
│   └── server.js                 HTTP entry point (port binding, shutdown)
│
├── .env                          Local config (not committed)
├── .env.example                  Template
└── package.json
```

---

## Switching the Frontend to Real Data

In `Frontend/.env`, set:

```env
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://localhost:5000
```

The frontend service layer (`src/services/index.ts`) will automatically use `apiStockService` instead of `mockStockService`.

---

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Invalid ticker format |
| 404 | Route not found |
| 422 | Ticker valid but no data available |
| 429 | Too many requests (rate limit: 60 req/min) |
| 500 | Internal server error |
| 502 | ML service returned malformed response |
| 503 | ML service unavailable (Python server down) |
| 504 | ML service timed out |
