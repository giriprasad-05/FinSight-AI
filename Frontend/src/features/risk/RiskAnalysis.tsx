import React from 'react';
import type { RiskAssessment } from '@/types';
import { Shield } from 'lucide-react';

interface RiskAnalysisProps {
  risk: RiskAssessment;
}

export function RiskAnalysis({ risk }: RiskAnalysisProps): React.ReactElement {
  return (
    <div className="card analysis-card">
      <div className="analysis-header analysis-header--risk">
        <Shield size={16} />
        AI Risk Assessment
      </div>
      
      <div className="analysis-score-wrap">
        <div className="analysis-score">
          {risk.riskScore} <span className="analysis-score__den">/ 100</span>
        </div>
        <div className="analysis-badge analysis-badge--moderate">
          {risk.riskLevel}
        </div>
      </div>

      <div className="analysis-factors">
        <div className="analysis-factors__title">Key Factors</div>
        {risk.factors.slice(0, 3).map((f, i) => (
          <div key={i} className="analysis-factor">
            {/* Display f.value (the real explanation text from the risk engine),
                not f.label which is the generic "Risk Factor N" label */}
            {f.value || f.label}
          </div>
        ))}
      </div>

      <div className="analysis-progress">
        <div className="analysis-progress__fill analysis-progress__fill--risk" style={{ width: `${risk.riskScore}%` }} />
        <div className="analysis-progress__knob analysis-progress__knob--risk" style={{ left: `${risk.riskScore}%` }} />
        <div className="analysis-progress-labels">
          <span>0</span>
          <span>50</span>
          <span>100</span>
        </div>
      </div>
    </div>
  );
}
