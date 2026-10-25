/**
 * stockService.js
 * ----------------
 * Thin wrapper around the Python ML service for stock-related data.
 * The Node backend does NOT fetch stock data itself — it proxies
 * requests to the FastAPI ML microservice via mlService.js.
 *
 * This module provides a business-logic layer for stock operations
 * that may combine multiple ML service calls in the future.
 */

import { fetchQuote, fetchAnalysis, fetchPrediction, fetchRisk, fetchExplanation, checkMlHealth } from './mlService.js';

// ── Re-export ML service calls under stock-oriented names ─────────

/**
 * Get latest quote and company info from Yahoo Finance via ML service.
 * @param {string} ticker  Validated ticker symbol
 * @returns {Promise<object>} Stock quote payload
 */
export async function getStockQuote(ticker) {
  return fetchQuote(ticker);
}

/**
 * Get the full combined analysis (trend + risk + explanation) for a ticker.
 * @param {string} ticker  Validated ticker symbol
 * @returns {Promise<object>} Combined analysis payload from Python ML service
 */
export async function getStockAnalysis(ticker) {
  return fetchAnalysis(ticker);
}

/**
 * Get AI explanation (trend, drivers, risk, watch items) for a ticker.
 * @param {string} ticker  Validated ticker symbol
 * @returns {Promise<object>} Explanation payload from Python ML service
 */
export async function getStockExplanation(ticker) {
  return fetchExplanation(ticker);
}

/**
 * Get trend prediction for a ticker.
 * @param {string} ticker  Validated ticker symbol
 * @returns {Promise<object>} Prediction payload from Python ML service
 */
export async function getStockPrediction(ticker) {
  return fetchPrediction(ticker);
}

/**
 * Get risk assessment for a ticker.
 * @param {string} ticker  Validated ticker symbol
 * @returns {Promise<object>} Risk payload from Python ML service
 */
export async function getStockRisk(ticker) {
  return fetchRisk(ticker);
}

/**
 * Health-check the Python ML service.
 * @returns {Promise<object>} Health payload
 */
export async function getMlHealth() {
  return checkMlHealth();
}
