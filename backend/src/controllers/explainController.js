/**
 * explainController.js
 * --------------------
 * Handles GET /api/explain/:ticker
 *
 * Proxies the request to the Python ML service /explain/{ticker} endpoint,
 * which generates deterministic explanations of model predictions, top drivers,
 * risk metrics, and watch items.
 */

import { getStockExplanation } from '../services/stockService.js';
import { validateTicker } from '../utils/tickerValidator.js';

/**
 * GET /api/explain/:ticker
 *
 * Delegates to Python /explain/{ticker}.
 * Returns structured explanation payload unchanged.
 */
export async function getExplanation(req, res, next) {
  const { valid, ticker, error } = validateTicker(req.params.ticker);
  if (!valid) {
    return res.status(400).json({ error, status: 400 });
  }

  try {
    const data = await getStockExplanation(ticker);

    if (!data || !data.summary) {
      const e = new Error('ML service returned an incomplete explanation response.');
      e.statusCode = 502;
      throw e;
    }

    res.json(data);
  } catch (err) {
    next(err);
  }
}
