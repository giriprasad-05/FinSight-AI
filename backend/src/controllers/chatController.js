/**
 * chatController.js
 * -----------------
 * Handles POST /api/chat
 *
 * Flow:
 *   1. Validate ticker symbol.
 *   2. Validate message.
 *   3. Retrieve the existing FinSight analysis for the ticker (delegates to FastAPI).
 *   4. Build compact stock context.
 *   5. Send stock context + conversation + system prompt to LM Studio.
 *   6. Return the local model response.
 */

import { validateTicker } from '../utils/tickerValidator.js';
import { getStockAnalysis } from '../services/stockService.js';
import { getStockChatResponse } from '../services/llmService.js';

/**
 * POST /api/chat
 *
 * Request body:
 * {
 *   "ticker": "AAPL",
 *   "message": "Why is the risk medium?",
 *   "conversation": [
 *     { "role": "user", "content": "Why is the risk medium?" }
 *   ]
 * }
 */
export async function handleStockChat(req, res, next) {
  const { ticker: rawTicker, message, conversation = [] } = req.body || {};

  // 1. Validate ticker
  const { valid, ticker, error: tickerError } = validateTicker(rawTicker);
  if (!valid) {
    return res.status(400).json({ error: tickerError, status: 400 });
  }

  // 2. Validate message
  if (typeof message !== 'string' || !message.trim()) {
    return res.status(400).json({ error: 'Message is required and must be a non-empty string.', status: 400 });
  }

  try {
    // 3. Retrieve existing FinSight analysis for the ticker
    const analysis = await getStockAnalysis(ticker);
    if (!analysis || !analysis.trend || !analysis.risk) {
      const e = new Error(`Incomplete FinSight analysis returned for ${ticker}.`);
      e.statusCode = 502;
      throw e;
    }

    // 4 & 5. Build compact context & generate response via LM Studio
    const result = await getStockChatResponse({
      ticker,
      message,
      conversation,
      analysis,
    });

    // 6. Return response
    return res.json({
      ticker: result.ticker,
      reply: result.reply,
      response: result.reply,
      model: result.model,
      stockContext: result.stockContext,
    });
  } catch (err) {
    // If local LLM is down/refused, return 503 with standardized message
    if (err.statusCode === 503 || err.message?.includes('unavailable') || err.message?.includes('ECONNREFUSED')) {
      return res.status(503).json({
        error: 'Local AI is unavailable.',
        detail: err.message,
        status: 503,
      });
    }
    next(err);
  }
}
