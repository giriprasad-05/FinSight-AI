import React, { useState } from 'react';
import {
  Lightbulb,
  ChevronDown,
  Shield,
  TrendingUp,
  TrendingDown,
  Minus,
  Eye,
  Activity,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import type { FeatureImportance, AIExplanation } from '@/types';

interface ExplainableAIProps {
  summary?: string;
  features?: FeatureImportance[];
  explanation?: AIExplanation;
  isLoading?: boolean;
  isError?: boolean;
}

export function ExplainableAI({
  summary: fallbackSummary,
  features: _fallbackFeatures,
  explanation,
  isLoading = false,
  isError = false,
}: ExplainableAIProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(true);

  // Derive display values from explanation or fallbacks
  const summaryText =
    explanation?.summary ||
    fallbackSummary ||
    'AI explanation is evaluating recent indicators and model attribution.';

  const prediction = explanation?.prediction;
  const confidence = explanation?.confidence;
  const riskLevel = explanation?.risk_level;
  const riskScore = explanation?.risk_score;
  const keyDrivers = explanation?.key_drivers ?? [];
  const trendExplanation = explanation?.trend_explanation;
  const riskExplanation = explanation?.risk_explanation;
  const watchItems = explanation?.watch_items ?? [];

  const getPredictionBadge = (pred?: string) => {
    if (!pred) return null;
    const isUp = pred.toUpperCase() === 'UP';
    const isDown = pred.toUpperCase() === 'DOWN';
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '2px 8px',
          borderRadius: 'var(--radius-sm)',
          fontSize: 'var(--font-size-xs)',
          fontWeight: 'var(--font-weight-semibold)',
          fontFamily: 'var(--font-mono)',
          background: isUp
            ? 'var(--color-gain-bg)'
            : isDown
            ? 'var(--color-loss-bg)'
            : 'var(--color-accent-subtle)',
          color: isUp
            ? 'var(--color-gain-text)'
            : isDown
            ? 'var(--color-loss-text)'
            : 'var(--color-text-secondary)',
          border: `1px solid ${
            isUp
              ? 'var(--color-gain)'
              : isDown
              ? 'var(--color-loss)'
              : 'var(--color-border)'
          }`,
        }}
      >
        {isUp && <TrendingUp size={12} />}
        {isDown && <TrendingDown size={12} />}
        {!isUp && !isDown && <Minus size={12} />}
        {pred.toUpperCase()}
      </span>
    );
  };

  const getRiskBadge = (lvl?: string) => {
    if (!lvl) return null;
    const upper = lvl.toUpperCase();
    const color =
      upper === 'LOW'
        ? 'var(--color-risk-low)'
        : upper === 'HIGH'
        ? 'var(--color-risk-high)'
        : 'var(--color-risk-medium)';

    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '2px 8px',
          borderRadius: 'var(--radius-sm)',
          fontSize: 'var(--font-size-xs)',
          fontWeight: 'var(--font-weight-medium)',
          fontFamily: 'var(--font-mono)',
          background: 'var(--color-bg-base)',
          color: color,
          border: `1px solid ${color}`,
        }}
      >
        <Shield size={11} />
        {lvl} Risk {riskScore !== undefined ? `(${riskScore.toFixed(0)})` : ''}
      </span>
    );
  };

  return (
    <div className="card explain-card">
      <button
        className="explain-toggle"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <div className="explain-title-wrap">
          <Lightbulb size={18} />
          <span>AI Explanation Engine</span>
        </div>

        <div className="explain-badges">
          {prediction && getPredictionBadge(prediction)}
          {confidence !== undefined && (
            <span
              style={{
                fontSize: 'var(--font-size-xs)',
                fontFamily: 'var(--font-mono)',
                color: 'var(--color-text-muted)',
              }}
            >
              {(confidence * 100).toFixed(0)}% conf
            </span>
          )}
          {riskLevel && getRiskBadge(riskLevel)}
          {explanation?.llm?.used && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 'var(--font-weight-medium)',
                fontFamily: 'var(--font-mono)',
                background: 'rgba(99, 102, 241, 0.15)',
                color: '#818cf8',
                border: '1px solid rgba(99, 102, 241, 0.35)',
              }}
              title={
                explanation.llm.model
                  ? `Polished by local model: ${explanation.llm.model}`
                  : 'Polished by local LLM'
              }
            >
              <Sparkles size={11} />
              Local AI explanation
            </span>
          )}
        </div>

        <ChevronDown
          size={16}
          className={`explain-chevron ${isOpen ? 'explain-chevron--open' : ''}`}
        />
      </button>

      {isOpen && (
        <div className="explain-content">
          {/* Loading State */}
          {isLoading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-4)',
                color: 'var(--color-text-muted)',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              <div
                className="spinner"
                style={{
                  width: '18px',
                  height: '18px',
                  borderWidth: '2px',
                  borderColor: 'var(--color-border)',
                  borderTopColor: 'var(--color-accent)',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }}
              />
              Generating model explanation and feature attribution...
            </div>
          )}

          {/* Error State */}
          {isError && !explanation && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                color: 'var(--color-warning)',
                fontSize: 'var(--font-size-sm)',
                padding: 'var(--space-3)',
                background: 'var(--color-warning-bg)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <AlertCircle size={16} />
              Explanation data could not be retrieved from the ML service. Displaying base analytics.
            </div>
          )}

          {/* Executive Summary */}
          <div className="explain-summary-box">
            {explanation?.headline && (
              <div
                style={{
                  fontWeight: 'var(--font-weight-semibold)',
                  color: 'var(--color-text-primary)',
                  marginBottom: 'var(--space-2)',
                  fontSize: 'var(--font-size-sm)',
                  lineHeight: 'var(--line-height-snug)',
                }}
              >
                {explanation.headline}
              </div>
            )}
            <div>{summaryText}</div>
          </div>

          {/* Directional Trend Explanation */}
          {trendExplanation && (
            <div className="explain-section">
              <div className="explain-section-title">
                <Activity size={13} />
                <span>Directional Trend Dynamics</span>
              </div>
              <div className="explain-section-desc">
                {trendExplanation}
              </div>
            </div>
          )}

          {/* Top 3 Model Drivers */}
          {keyDrivers.length > 0 && (
            <div className="explain-section">
              <div className="explain-section-title">
                <Lightbulb size={13} />
                <span>Top Model Drivers &amp; Feature Attribution</span>
              </div>
              <div className="explain-drivers-grid">
                {keyDrivers.slice(0, 3).map((driver, index) => (
                  <div key={driver.feature || index} className="explain-driver-card">
                    <div className="explain-driver-header">
                      <span className="explain-driver-name">{driver.name}</span>
                      <div className="explain-driver-meta">
                        <span className="explain-driver-val">{driver.value}</span>
                        <span className="explain-driver-imp">
                          {(driver.importance * 100).toFixed(1)}% imp
                        </span>
                      </div>
                    </div>
                    <p className="explain-driver-desc">{driver.explanation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quantitative Risk Explanation */}
          {riskExplanation && (
            <div className="explain-section">
              <div className="explain-section-title">
                <Shield size={13} />
                <span>Quantitative Risk Assessment</span>
              </div>
              <div className="explain-section-desc">
                {riskExplanation}
              </div>
            </div>
          )}

          {/* Watch Items */}
          {watchItems.length > 0 && (
            <div className="explain-section">
              <div className="explain-section-title">
                <Eye size={13} />
                <span>Key Factors to Watch</span>
              </div>
              <div className="explain-watch-list">
                {watchItems.map((item, idx) => (
                  <div key={idx} className="explain-watch-item">
                    <Eye size={14} />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Financial Safety Disclaimer */}
          <div className="explain-disclaimer">
            FinSight AI explanations interpret statistical model outputs and technical indicators.
            They do not constitute investment advice or recommendations to buy or sell securities.
          </div>
        </div>
      )}
    </div>
  );
}
