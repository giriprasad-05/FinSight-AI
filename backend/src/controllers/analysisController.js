/**
 * analysisController.js
 * ----------------------
 * Handles GET /api/analysis/:ticker
 *
 * Returns the combined trend + risk analysis by delegating to the
 * Python /analysis/{ticker} endpoint (which runs both engines concurrently).
 *
 * The Node backend does NOT modify the ML output in any way.
 */

import { getStockAnalysis } from '../services/stockService.js';
import { validateTicker } from '../utils/tickerValidator.js';

/**
 * GET /api/analysis/:ticker
 *
 * Delegates to Python /analysis/{ticker}.
 * Returns combined prediction + risk data unchanged.
 *
 * Example response:
 * {
 *   "ticker": "AAPL",
 *   "market": "US",
 *   "data_date": "2024-01-15",
 *   "trend": {
 *     "prediction": "UP",
 *     "prediction_code": 2,
 *     "confidence": 0.61,
 *     "probabilities": { "DOWN": 0.17, "FLAT": 0.22, "UP": 0.61 },
 *     "model_version": "v2"
 *   },
 *   "risk": {
 *     "risk_score": 39.1,
 *     "risk_level": "MEDIUM",
 *     "components": { ... },
 *     "raw_metrics": { ... },
 *     "explanations": [ ... ]
 *   },
 *   "indicators": { ... }
 * }
 */
export async function getAnalysis(req, res, next) {
  const { valid, ticker, error } = validateTicker(req.params.ticker);
  if (!valid) {
    return res.status(400).json({ error, status: 400 });
  }

  try {
    const data = await getStockAnalysis(ticker);

    // Guard: ensure the combined response has both sections
    if (!data || !data.trend || !data.risk) {
      const e = new Error('ML service returned an incomplete analysis response.');
      e.statusCode = 502;
      throw e;
    }

    res.json(data);
  } catch (err) {
    next(err);
  }
}
