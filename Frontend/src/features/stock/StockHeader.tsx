import React from 'react';
import type { StockDetail } from '@/types';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { format } from 'date-fns';

interface StockHeaderProps {
  stock: StockDetail;
}

export function StockHeader({ stock }: StockHeaderProps): React.ReactElement {
  const isGain = stock.priceChange >= 0;

  return (
    <div className="stock-identity">
      <div className="stock-identity__title">{stock.name}</div>
      <div className="stock-identity__ticker">{stock.ticker}</div>

      <div className="stock-price">
        {formatCurrency(stock.price)}
      </div>
      <div className={`stock-change stock-change--${isGain ? 'gain' : 'loss'}`}>
        <span>{isGain ? '+' : ''}{formatCurrency(stock.priceChange)}</span>
        <span>{isGain ? '+' : ''}{formatPercent(stock.priceChangePct)}</span>
      </div>
      
      <div className="stock-timestamp">
        As of {format(new Date(), 'MMM d, yyyy h:mm a')} EDT
      </div>
    </div>
  );
}
