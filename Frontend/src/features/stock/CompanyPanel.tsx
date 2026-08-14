import React from 'react';
import type { StockDetail } from '@/types';
import { formatCurrency, formatVolume } from '@/lib/utils';

interface CompanyPanelProps {
  stock: StockDetail;
}

export function CompanyPanel({ stock }: CompanyPanelProps): React.ReactElement {
  const metrics = [
    { label: 'Company',     value: stock.name },
    { label: 'Sector',      value: stock.sector },
    { label: 'Industry',    value: stock.industry },
    { label: 'Market Cap',  value: formatCurrency(stock.marketCap, true) },
    { label: 'P/E Ratio',   value: stock.peRatio != null ? stock.peRatio.toFixed(1) : 'N/A' },
    { label: 'Volume',      value: formatVolume(stock.volume) },
    { label: '52 Week High', value: formatCurrency(stock.yearHigh) },
    { label: '52 Week Low',  value: formatCurrency(stock.yearLow) },
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
