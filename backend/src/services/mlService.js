/**
 * mlService.js
 * Axios client that communicates with the Python FastAPI ML microservice.
 * All ML logic lives in Python — this module only makes HTTP calls.
 */

import axios from 'axios';
import 'dotenv/config';

const ML_BASE = process.env.ML_SERVICE_URL || 'http://127.0.0.1:8000';
const ML_TIMEOUT = parseInt(process.env.ML_TIMEOUT_MS || '30000', 10);

const mlClient = axios.create({
  baseURL: ML_BASE,
  timeout: ML_TIMEOUT,
  headers: { 'Content-Type': 'application/json' },
});

// ── Response interceptor: unwrap data, normalise errors ─────────────
mlClient.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.code === 'ECONNREFUSED' || err.code === 'ENOTFOUND') {
      const e = new Error('ML service is unavailable. Is the Python server running?');
      e.statusCode = 503;
      throw e;
    }
    if (err.code === 'ECONNABORTED') {
      const e = new Error(`ML service timed out after ${ML_TIMEOUT}ms.`);
      e.statusCode = 504;
      throw e;
    }
    if (err.response) {
      const detail = err.response.data?.detail || err.response.statusText;
      const e = new Error(detail);
      e.statusCode = err.response.status;
      throw e;
    }
    throw err;
  }
);

/**
 * Health check against the Python ML service.
 * @returns {Promise<object>} Health payload
 */
export async function checkMlHealth() {
  return mlClient.get('/health');
}

/**
 * Trend prediction for a ticker.
 * @param {string} ticker
 * @returns {Promise<object>} Prediction payload
 */
export async function fetchPrediction(ticker) {
  return mlClient.get(`/predict/${encodeURIComponent(ticker)}`);
}

/**
 * Risk assessment for a ticker.
 * @param {string} ticker
 * @returns {Promise<object>} Risk payload
 */
export async function fetchRisk(ticker) {
  return mlClient.get(`/risk/${encodeURIComponent(ticker)}`);
}

/**
 * Combined analysis (trend + risk) for a ticker.
 * @param {string} ticker
 * @returns {Promise<object>} Combined analysis payload
 */
export async function fetchAnalysis(ticker) {
  return mlClient.get(`/analysis/${encodeURIComponent(ticker)}`);
}

/**
 * AI explanation (trend interpretation, key drivers, risk, watch items) for a ticker.
 * @param {string} ticker
 * @returns {Promise<object>} Explanation payload
 */
export async function fetchExplanation(ticker) {
  return mlClient.get(`/explain/${encodeURIComponent(ticker)}`);
}

/**
 * Real-time/latest quote + company info for a ticker.
 * Calls the Python /quote/{ticker} endpoint which uses yfinance.
 * @param {string} ticker
 * @returns {Promise<object>} Quote payload
 */
export async function fetchQuote(ticker) {
  return mlClient.get(`/quote/${encodeURIComponent(ticker)}`);
}

/**
 * Historical OHLCV data for charting.
 * Calls the Python /quote/{ticker}/history endpoint which uses yfinance.
 * @param {string} ticker
 * @param {string} range  One of: 1W|1M|3M|6M|1Y|5Y
 * @returns {Promise<Array>} Array of {date, open, high, low, close, volume}
 */
export async function fetchHistory(ticker, range) {
  return mlClient.get(
    `/quote/${encodeURIComponent(ticker)}/history?range=${encodeURIComponent(range)}`
  );
}

/**
 * Search the supported stock universe.
 * Calls the Python /search/{query} endpoint.
 * @param {string} query  Ticker symbol or partial name
 * @returns {Promise<Array>} Array of {ticker, company_name, market, currency, exchange}
 */
export async function fetchSearch(query) {
  return mlClient.get(`/search/${encodeURIComponent(query)}`);
}
