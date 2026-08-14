import React from 'react';
import type { TrendAnalysis as TrendAnalysisType } from '@/types';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface TrendAnalysisProps {
  trend: TrendAnalysisType;
}

export function TrendAnalysis({ trend }: TrendAnalysisProps): React.ReactElement {
  const isBullish = trend.direction === 'Bullish';
  const isBearish = trend.direction === 'Bearish';
  const Icon = isBullish ? TrendingUp : isBearish ? TrendingDown : Minus;
  
  return (
    <div className="card analysis-card">
      <div className="analysis-header analysis-header--trend">
        <Icon size={16} />
        AI Trend Analysis
      </div>
      
      <div className="analysis-score-wrap">
        <div className="analysis-score" style={{ color: isBullish ? 'var(--color-gain-text)' : isBearish ? 'var(--color-loss-text)' : 'inherit' }}>
          {trend.direction.toUpperCase()}
        </div>
        <div className="analysis-subtitle">
          {trend.confidence}% confidence
        </div>
      </div>

      <div className="analysis-factors">
        <div className="analysis-factors__title">Key Drivers</div>
        {trend.signals.slice(0, 3).map((s, i) => (
          <div key={i} className="analysis-factor">
            {s.label} ({s.value})
          </div>
        ))}
      </div>

      <div className="analysis-progress">
        <div className="analysis-progress__fill analysis-progress__fill--trend" style={{ width: `${trend.confidence}%` }} />
        <div className="analysis-progress__knob analysis-progress__knob--trend" style={{ left: `${trend.confidence}%` }} />
        <div className="analysis-progress-labels">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  );
}
