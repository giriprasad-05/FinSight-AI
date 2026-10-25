/**
 * predictionController.js
 * ------------------------
 * Handles GET /api/predictions/:ticker
 *
 * Validates the ticker, calls the Python ML service prediction endpoint,
 * and returns the unmodified result to the React frontend.
 *
 * The Node backend does NOT alter prediction probabilities or confidence.
 */

import { getStockPrediction } from '../services/stockService.js';
import { validateTicker } from '../utils/tickerValidator.js';

/**
 * GET /api/predictions/:ticker
 *
 * Delegates to Python /predict/{ticker}.
 * Returns prediction unchanged — shape is owned by the ML service.
 *
 * Example response:
 * {
 *   "ticker": "AAPL",
 *   "market": "US",
 *   "data_date": "2024-01-15",
 *   "prediction": "UP",
 *   "prediction_code": 2,
 *   "confidence": 0.61,
 *   "probabilities": { "DOWN": 0.17, "FLAT": 0.22, "UP": 0.61 },
 *   "indicators": { ... },
 *   "model_version": "v2"
 * }
 */
export async function getPrediction(req, res, next) {
  const { valid, ticker, error } = validateTicker(req.params.ticker);
  if (!valid) {
    return res.status(400).json({ error, status: 400 });
  }

  try {
    const data = await getStockPrediction(ticker);

    // Guard: ML service returned an empty/unexpected payload
    if (!data || !data.prediction) {
      const e = new Error('ML service returned an empty prediction result.');
      e.statusCode = 502;
      throw e;
    }

    res.json(data);
  } catch (err) {
    next(err);
  }
}
