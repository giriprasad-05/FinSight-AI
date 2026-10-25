# FinSight AI - Stock Prediction ML Service

A dedicated Python machine learning microservice for stock market forecasting, trend analysis, and risk evaluation using **XGBoost**.

---

## 📁 Directory Structure

```text
ml-service/
│
├── data/
│   ├── raw/                # Cached raw historical market data (OHLCV)
│   └── processed/          # Preprocessed feature matrices & training sets
│
├── models/                 # Saved model weights & scalers (.json, .pkl)
│
├── src/
│   ├── __init__.py         # Package initializer
│   ├── data_fetcher.py     # Data ingestion & historical fetching via yfinance
│   ├── features.py         # Technical indicators & feature engineering pipeline
│   ├── train.py            # XGBoost training, hyperparameter tuning & checkpointing
│   ├── predict.py          # Model inference & prediction generation
│   └── evaluate.py         # Performance evaluation (RMSE, accuracy, financial metrics)
│
├── main.py                 # FastAPI application & REST endpoint definitions
├── requirements.txt        # Python dependency manifest
└── README.md               # Service documentation
```

---

## 📦 Planned Dependencies

- **`pandas`**: Data manipulation and tabular time-series structures.
- **`numpy`**: Numerical array computation and vector operations.
- **`scikit-learn`**: Preprocessing scalers, cross-validation, and evaluation metrics.
- **`xgboost`**: Gradient boosted decision trees for time-series forecasting.
- **`yfinance`**: Financial market data retrieval.
- **`fastapi`**: Modern, fast web framework for building APIs.
- **`uvicorn`**: High-performance ASGI web server.

---

## 🔄 Backend Communication Flow

This microservice communicates with the existing backend via a lightweight **RESTful API** over HTTP:

1. **Client / Backend Request**: The main backend server (Node.js / Express / Django / FastAPI) sends an HTTP request (e.g., `POST /predict` or `GET /predict/{ticker}`) with target parameters (ticker symbol, timeframe, indicators).
2. **Inference / Processing**: The ML service retrieves required market features, runs inference through the trained XGBoost model in `predict.py`, and computes confidence/risk scores.
3. **Structured Response**: The ML service returns a structured JSON payload containing predictions, probabilities, and technical rationale back to the backend.
4. **Delivery to Frontend**: The backend forwards or integrates this prediction data into its response to the React frontend.
