/**
 * tickerValidator.js
 * -------------------
 * Clean, safe ticker validation for both US and Indian NSE/BSE tickers.
 *
 * Strategy:
 *   - Whitelist character set: letters, digits, dots, hyphens.
 *   - Length: 1–20 characters (covers "A" through "BERKSHIRE-A.NS" etc.).
 *   - Reject empty strings and strings with unsafe characters.
 *   - No hard-coded symbol allow-list: any well-formed ticker passes.
 *   - Always returns the upper-cased ticker.
 *
 * Examples of valid tickers:
 *   AAPL, MSFT, NVDA, BRK-B, RELIANCE.NS, TCS.NS, INFY.NS
 *
 * Examples of invalid tickers:
 *   "", "  ", "AAPL; DROP TABLE", "../etc/passwd", "A".repeat(21)
 */

// Only allow: letters, digits, dots, hyphens.  Max 20 chars.
const TICKER_REGEX = /^[A-Z0-9.\-]{1,20}$/;

/**
 * Validates and normalises a ticker symbol.
 *
 * @param {string|any} raw  The raw ticker input (from req.params or query).
 * @returns {{ valid: boolean, ticker: string|null, error: string|null }}
 */
export function validateTicker(raw) {
  if (typeof raw !== 'string') {
    return { valid: false, ticker: null, error: 'Ticker must be a string.' };
  }

  const t = raw.trim().toUpperCase();

  if (!t) {
    return { valid: false, ticker: null, error: 'Ticker symbol is required.' };
  }

  if (!TICKER_REGEX.test(t)) {
    return {
      valid: false,
      ticker: null,
      error: `Invalid ticker format: "${t}". Only letters, digits, dots, and hyphens are allowed (max 20 characters).`,
    };
  }

  return { valid: true, ticker: t, error: null };
}
