import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useStockStore } from '@/store/stockStore';
import { useMentorStore } from '@/store/mentorStore';
import {
  useStockDetail,
  usePriceHistory,
  useRiskAssessment,
  useTrendAnalysis,
  useStockExplanation,
} from '@/hooks/useStockData';

import { StockHeader } from '@/features/stock/StockHeader';
import { CompanyPanel } from '@/features/stock/CompanyPanel';
import { PriceChart } from '@/features/chart/PriceChart';
import { RiskAnalysis } from '@/features/risk/RiskAnalysis';
import { TrendAnalysis } from '@/features/risk/TrendAnalysis';
import { ExplainableAI } from '@/features/explainability/ExplainableAI';
import { InvestmentMentor } from '@/features/mentor/InvestmentMentor';

function DashboardSkeleton(): React.ReactElement {
  return (
    <div className="workspace">
      <div className="header-section">
        <div className="skeleton skeleton-h1 skeleton-block" style={{ width: '40%' }} />
        <div className="skeleton skeleton-h2 skeleton-block" style={{ width: '40%' }} />
      </div>
      <div className="main-grid">
        <div className="card" style={{ height: '300px' }} />
        <div className="card" style={{ height: '300px' }} />
        <div className="card" style={{ height: '300px' }} />
      </div>
    </div>
  );
}

function StockNotFound({ ticker }: { ticker: string }): React.ReactElement {
  const navigate = useNavigate();
  return (
    <div className="workspace" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 'var(--space-16)' }}>
      <div style={{ fontSize: '2rem', marginBottom: 'var(--space-4)' }}>🔍</div>
      <h2 style={{ fontSize: 'var(--font-size-xl)' }}>Stock not found</h2>
      <p style={{ color: 'var(--color-text-muted)', marginTop: 'var(--space-2)' }}>
        No data available for "{ticker}".
      </p>
      <button className="btn btn--primary" style={{ marginTop: 'var(--space-6)' }} onClick={() => navigate('/')}>
        Back to Home
      </button>
    </div>
  );
}

export function StockDashboard(): React.ReactElement {
  const { ticker: urlTicker } = useParams<{ ticker: string }>();
  const ticker = urlTicker?.toUpperCase() ?? null;

  const timeRange = useStockStore(s => s.timeRange);
  const setTimeRange = useStockStore(s => s.setTimeRange);
  const selectStock = useStockStore(s => s.selectStock);

  const setMentorContext = useMentorStore(s => s.setContext);

  useEffect(() => {
    if (ticker) selectStock(ticker);
  }, [ticker, selectStock]);

  const stockQuery   = useStockDetail(ticker);
  const historyQuery = usePriceHistory(ticker, timeRange);
  const riskQuery    = useRiskAssessment(ticker);
  const trendQuery   = useTrendAnalysis(ticker);
  const explainQuery = useStockExplanation(ticker);

  useEffect(() => {
    const s = stockQuery.data;
    const r = riskQuery.data;
    const t = trendQuery.data;
    if (s && r && t) {
      setMentorContext({
        ticker: s.ticker,
        companyName: s.name,
        riskLevel: r.riskLevel,
        riskScore: r.riskScore,
        trendDirection: t.direction,
        price: s.price,
        priceChangePct: s.priceChangePct,
      });
    }
  }, [stockQuery.data, riskQuery.data, trendQuery.data, setMentorContext]);

  if (stockQuery.isError) {
    return <StockNotFound ticker={ticker ?? ''} />;
  }

  if (stockQuery.isLoading) {
    return <DashboardSkeleton />;
  }

  const stock = stockQuery.data;
  if (!stock) return <div />;

  return (
    <div className="workspace">
      
      <div className="header-section">
        <StockHeader stock={stock} />
        <CompanyPanel stock={stock} />
      </div>

      <div className="main-grid">
        <PriceChart 
          data={historyQuery.data ?? []} 
          range={timeRange} 
          onRangeChange={setTimeRange} 
          isLoading={historyQuery.isLoading} 
        />
        {riskQuery.data && <RiskAnalysis risk={riskQuery.data} />}
        {trendQuery.data && <TrendAnalysis trend={trendQuery.data} />}
      </div>

      <ExplainableAI 
        explanation={explainQuery.data}
        isLoading={explainQuery.isLoading}
        isError={explainQuery.isError}
        summary={riskQuery.data?.summary} 
        features={riskQuery.data?.featureImportances} 
      />

      <div className="bottom-grid">
        <InvestmentMentor />
      </div>

    </div>
  );
}
