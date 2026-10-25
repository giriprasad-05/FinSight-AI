import React from 'react';
import type { StockDetail } from '@/types';
import { formatVolume } from '@/lib/utils';

interface CompanyPanelProps {
  stock: StockDetail;
}

/**
 * Format a market cap value with the correct currency symbol.
 * Returns "N/A" when the value is genuinely unavailable (null/0).
 */
function formatMarketCap(value: number | null | undefined, currency?: string): string {
  if (!value || value === 0) return 'N/A';
  const curr = currency ?? 'USD';
  const symbol = curr === 'INR' ? '₹' : '$';

  if (Math.abs(value) >= 1e12) return `${symbol}${(value / 1e12).toFixed(2)}T`;
  if (Math.abs(value) >= 1e9)  return `${symbol}${(value / 1e9).toFixed(2)}B`;
  if (Math.abs(value) >= 1e6)  return `${symbol}${(value / 1e6).toFixed(2)}M`;
  if (Math.abs(value) >= 1e3)  return `${symbol}${(value / 1e3).toFixed(1)}K`;
  return `${symbol}${value.toFixed(2)}`;
}

/**
 * Format a price with the correct currency symbol.
 * Returns "N/A" when the value is genuinely unavailable (null/0).
 */
function formatPriceValue(value: number | null | undefined, currency?: string): string {
  if (value === null || value === undefined || value === 0) return 'N/A';
  const curr = currency ?? 'USD';
  if (curr === 'INR') {
    return `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: curr,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function CompanyPanel({ stock }: CompanyPanelProps): React.ReactElement {
  const currency = stock.currency;

  const metrics = [
    { label: 'Company',      value: stock.name || 'N/A' },
    { label: 'Sector',       value: stock.sector && stock.sector !== 'N/A' ? stock.sector : 'N/A' },
    { label: 'Industry',     value: stock.industry && stock.industry !== 'N/A' ? stock.industry : 'N/A' },
    { label: 'Market Cap',   value: formatMarketCap(stock.marketCap, currency) },
    { label: 'P/E Ratio',    value: stock.peRatio != null ? stock.peRatio.toFixed(1) : 'N/A' },
    { label: 'Volume',       value: stock.volume ? formatVolume(stock.volume) : 'N/A' },
    { label: '52 Week High', value: formatPriceValue(stock.yearHigh, currency) },
    { label: '52 Week Low',  value: formatPriceValue(stock.yearLow, currency) },
  ];

  return (
    <div className="company-info">
      <div className="company-info__title">Company Information</div>
      <div className="company-info__grid">
        {metrics.map(m => (
          <div key={m.label} className="company-metric">
            <span className="company-metric__label">{m.label}</span>
            <span className="company-metric__value">{m.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
