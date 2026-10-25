/**
 * riskController.js
 * ------------------
 * Handles GET /api/risk/:ticker
 *
 * Validates the ticker, calls the Python ML service risk endpoint,
 * and returns the unmodified result to the React frontend.
 *
 * The Node backend does NOT recalculate or modify risk scores.
 */

import { getStockRisk } from '../services/stockService.js';
import { validateTicker } from '../utils/tickerValidator.js';

/**
 * GET /api/risk/:ticker
 *
 * Delegates to Python /risk/{ticker}.
 * Returns risk result unchanged — shape is owned by the ML service.
 *
 * Example response:
 * {
 *   "ticker": "AAPL",
 *   "data_date": "2024-01-15",
 *   "risk_score": 39.1,
 *   "risk_level": "MEDIUM",
 *   "components": { ... },
 *   "raw_metrics": { ... },
 *   "explanations": [ ... ]
 * }
 */
export async function getRisk(req, res, next) {
  const { valid, ticker, error } = validateTicker(req.params.ticker);
  if (!valid) {
    return res.status(400).json({ error, status: 400 });
  }

  try {
    const data = await getStockRisk(ticker);

    // Guard: ML service returned an empty/unexpected payload
    if (!data || typeof data.risk_score !== 'number') {
      const e = new Error('ML service returned an empty risk assessment result.');
      e.statusCode = 502;
      throw e;
    }

    res.json(data);
  } catch (err) {
    next(err);
  }
}
