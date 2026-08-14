import React from 'react';
import type { StockDetail } from '@/types';
import { formatCurrency, formatNumber } from '@/lib/utils';

interface CompanyOverviewProps {
  stock: StockDetail;
}

export function CompanyOverview({ stock }: CompanyOverviewProps): React.ReactElement {
  return (
    <div className="company-overview card">
      <div className="card__header">
        <div className="card__title">🏢 Company Overview</div>
      </div>

      <p className="company-overview__desc">{stock.description}</p>

      <div className="company-metrics-grid">
        <div className="metric">
          <span className="metric__label">CEO</span>
          <span className="metric__value" style={{ fontFamily: 'inherit', fontWeight: 500, fontSize: 'var(--font-size-sm)' }}>
            {stock.ceo}
          </span>
        </div>
        <div className="metric">
          <span className="metric__label">Industry</span>
          <span className="metric__value" style={{ fontFamily: 'inherit', fontWeight: 500, fontSize: 'var(--font-size-sm)' }}>
            {stock.industry}
          </span>
        </div>
        <div className="metric">
          <span className="metric__label">Headquarters</span>
          <span className="metric__value" style={{ fontFamily: 'inherit', fontWeight: 500, fontSize: 'var(--font-size-sm)' }}>
            {stock.country}
          </span>
        </div>
        <div className="metric">
          <span className="metric__label">Employees</span>
          <span className="metric__value">{formatNumber(stock.employees)}</span>
        </div>
        <div className="metric">
          <span className="metric__label">Founded</span>
          <span className="metric__value">{stock.founded}</span>
        </div>
        <div className="metric">
          <span className="metric__label">Market Cap</span>
          <span className="metric__value">{formatCurrency(stock.marketCap, true)}</span>
        </div>
      </div>
    </div>
  );
}
