import React from 'react';
import type { StockDetail } from '@/types';
import { formatPercent } from '@/lib/utils';

interface StockHeaderProps {
  stock: StockDetail;
}

/**
 * Format a price with the correct currency symbol.
 * Uses the currency field from the quote data so INR stocks show ₹ not $.
 */
function formatPrice(value: number, currency?: string): string {
  const safeValue = value ?? 0;
  const curr = currency ?? 'USD';

  if (curr === 'INR') {
    // Indian Rupee formatting
    if (Math.abs(safeValue) >= 1e7) return `₹${(safeValue / 1e7).toFixed(2)}Cr`;
    if (Math.abs(safeValue) >= 1e5) return `₹${(safeValue / 1e5).toFixed(2)}L`;
    return `₹${safeValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  // Default: USD
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: curr,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(safeValue);
}

/**
 * Format the quote timestamp from the backend.
 * The backend returns an ISO 8601 string from yfinance (e.g. "2025-08-27T20:00:00+00:00").
 * We display it in a human-readable form and indicate it is delayed data.
 */
function formatQuoteTimestamp(isoTimestamp: string | null | undefined, market?: string): string {
  if (!isoTimestamp) {
    return 'Timestamp unavailable';
  }
  try {
    const dt = new Date(isoTimestamp);
    if (isNaN(dt.getTime())) return 'Timestamp unavailable';

    // Format in the user's local timezone
    const formatted = dt.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }) + ' ' + dt.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
    });

    const marketLabel = market ? ` [${market}]` : '';
    return `As of ${formatted}${marketLabel} (delayed)`;
  } catch {
    return 'Timestamp unavailable';
  }
}

export function StockHeader({ stock }: StockHeaderProps): React.ReactElement {
  const isGain = (stock.priceChange ?? 0) >= 0;
  const currency = stock.currency;
  const changeAbs = stock.priceChange ?? 0;
  const changePct = stock.priceChangePct ?? 0;

  // Format the price change in the correct currency
  const changeSign = isGain ? '+' : '';
  const changeAbsFormatted =
    currency === 'INR'
      ? `${changeSign}₹${Math.abs(changeAbs).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : `${changeSign}${formatPrice(changeAbs, currency)}`;

  return (
    <div className="stock-identity">
      <div className="stock-identity__title">{stock.name}</div>
      <div className="stock-identity__ticker">{stock.ticker}</div>

      <div className="stock-price">
        {formatPrice(stock.price, currency)}
      </div>
      <div className={`stock-change stock-change--${isGain ? 'gain' : 'loss'}`}>
        <span>{changeAbsFormatted}</span>
        <span>{changeSign}{formatPercent(Math.abs(changePct))}</span>
      </div>

      <div className="stock-timestamp">
        {formatQuoteTimestamp(stock.quoteTimestamp, stock.market)}
      </div>
    </div>
  );
}
