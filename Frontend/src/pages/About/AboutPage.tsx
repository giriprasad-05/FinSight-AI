import React from 'react';
import {
  TrendingUp,
  ShieldAlert,
  BrainCircuit,
  Cpu,
  BarChart2,
  Lock,
  Layers,
} from 'lucide-react';
import './AboutPage.css';

export function AboutPage(): React.ReactElement {
  return (
    <div className="about-page">
      {/* ── Hero / Purpose ───────────────────────────────── */}
      <section className="about-hero">
        <div className="about-hero__badge">
          <BrainCircuit size={14} />
          FinSight AI Architecture & Capabilities
        </div>
        <h1 className="about-hero__title">
          Institutional Financial Analytics & Explainable AI
        </h1>
        <p className="about-hero__desc">
          FinSight AI is an intelligent financial intelligence platform designed to bridge
          quantitative market data, machine learning directional forecasting, multi-factor risk
          modeling, and transparent explainable AI. By integrating local neural narrative synthesis,
          investors obtain actionable clarity with total privacy and zero external cloud exposure.
        </p>
      </section>

      {/* ── Key Features ─────────────────────────────────── */}
      <section>
        <h2 className="about-section-title">
          <Layers size={20} />
          Core Platform Capabilities
        </h2>
        <div className="about-grid">
          <div className="about-card">
            <div className="about-card__icon">
              <BarChart2 size={20} />
            </div>
            <h3 className="about-card__title">Real-Time Stock Analytics</h3>
            <p className="about-card__text">
              Provides live quote updates, multi-timeframe price history (1D to 5Y), moving
              averages (SMA 20, SMA 50), high/low ranges, trading volumes, and company profile
              diagnostics.
            </p>
            <span className="about-card__tag">Technical Analysis</span>
          </div>

          <div className="about-card">
            <div className="about-card__icon">
              <TrendingUp size={20} />
            </div>
            <h3 className="about-card__title">ML Directional Forecasting</h3>
            <p className="about-card__text">
              Leverages an XGBoost gradient boosting classifier trained on historical technical
              momentum, volume anomalies, and volatility regimes to forecast short-term directional
              trends (UP, DOWN, FLAT) with probabilistic confidence scores.
            </p>
            <span className="about-card__tag">XGBoost Classifier</span>
          </div>

          <div className="about-card">
            <div className="about-card__icon">
              <ShieldAlert size={20} />
            </div>
            <h3 className="about-card__title">Multi-Factor Risk Analysis</h3>
            <p className="about-card__text">
              Quantifies asset risk profiles using annualized volatility, beta sensitivity against
              market benchmarks, maximum historical drawdown, and volume stability to produce
              stratified Low, Medium, High, and Very High risk ratings.
            </p>
            <span className="about-card__tag">Risk Modeling</span>
          </div>

          <div className="about-card">
            <div className="about-card__icon">
              <BrainCircuit size={20} />
            </div>
            <h3 className="about-card__title">Explainable AI (XAI)</h3>
            <p className="about-card__text">
              Demystifies machine learning predictions through gain-based feature importance
              metrics. Users can clearly inspect the exact market signals (RSI 14, 5-day return,
              MACD, historical spread) driving algorithmic conclusions.
            </p>
            <span className="about-card__tag">Feature Importance</span>
          </div>

          <div className="about-card">
            <div className="about-card__icon">
              <Cpu size={20} />
            </div>
            <h3 className="about-card__title">Local AI Narrative & Mentor</h3>
            <p className="about-card__text">
              Powered by an on-device LM Studio integration, FinSight AI synthesizes natural
              language portfolio explanations and interactive investment mentorship directly on
              your machine, guaranteeing zero data leakage and ultra-low latency.
            </p>
            <span className="about-card__tag">Local LM Studio</span>
          </div>

          <div className="about-card">
            <div className="about-card__icon">
              <Lock size={20} />
            </div>
            <h3 className="about-card__title">Secure Access Control</h3>
            <p className="about-card__text">
              Features cryptographic authentication with scrypt key derivation, timing-safe
              password verification, and cryptographically signed session tokens to safeguard
              analytical workspaces and API endpoints.
            </p>
            <span className="about-card__tag">Secure Token Auth</span>
          </div>
        </div>
      </section>

      {/* ── System Architecture ──────────────────────────── */}
      <section className="about-arch">
        <h2 className="about-section-title" style={{ marginBottom: 'var(--space-2)' }}>
          <Cpu size={20} />
          System Architecture
        </h2>
        <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
          FinSight AI operates a decoupled 3-tier architecture ensuring maximum performance, modularity, and security:
        </p>

        <div className="about-arch__list">
          <div className="about-arch__item">
            <div className="about-arch__layer">Frontend Layer</div>
            <div className="about-arch__tech">React 19 & Vite</div>
            <div className="about-arch__desc">
              High-performance dark glassmorphic interface with TanStack Query caching and Zustand state management.
            </div>
          </div>

          <div className="about-arch__item">
            <div className="about-arch__layer">API Gateway Layer</div>
            <div className="about-arch__tech">Node.js & Express</div>
            <div className="about-arch__desc">
              Rate-limited API gateway orchestrating token authentication, security headers (Helmet), and ML proxying.
            </div>
          </div>

          <div className="about-arch__item">
            <div className="about-arch__layer">Machine Learning Engine</div>
            <div className="about-arch__tech">Python & FastAPI</div>
            <div className="about-arch__desc">
              FastAPI microservice executing trained XGBoost forecasting models, feature computation, and Yahoo Finance feeds.
            </div>
          </div>

          <div className="about-arch__item">
            <div className="about-arch__layer">Generative AI Engine</div>
            <div className="about-arch__tech">LM Studio Local LLM</div>
            <div className="about-arch__desc">
              Private local LLM runtime providing interactive financial explanations without cloud reliance.
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
