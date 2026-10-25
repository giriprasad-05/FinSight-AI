// ── Risk & Trend types ───────────────────────────────────────

export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Very High';

export type TrendDirection = 'Bullish' | 'Bearish' | 'Neutral' | 'Volatile';

export interface RiskFactor {
  label: string;
  value: string;
  impact: 'positive' | 'negative' | 'neutral';
  weight: number;   // 0–1, how much this factor contributes
}

export interface FeatureImportance {
  feature: string;
  importance: number;  // 0–100
  direction: 'positive' | 'negative';
  description: string;
}

export interface RiskAssessment {
  ticker: string;
  riskScore: number;         // 0–100
  riskLevel: RiskLevel;
  confidence: number;        // 0–100 (model confidence %)
  factors: RiskFactor[];
  featureImportances: FeatureImportance[];
  summary: string;
  educationalNote: string;
  modelVersion: string;
  generatedAt: string;       // ISO timestamp
}

export interface TrendSignal {
  label: string;
  value: string;
  supportingData: string;
}

export interface TrendAnalysis {
  ticker: string;
  direction: TrendDirection;
  strength: number;          // 0–100
  confidence: number;        // 0–100
  shortTermOutlook: string;  // 1–4 week narrative
  longTermOutlook: string;   // 3–12 month narrative
  signals: TrendSignal[];
  featureImportances: FeatureImportance[];
  disclaimer: string;
  generatedAt: string;
}

export interface EducationalInsight {
  ticker: string;
  concept: string;           // e.g. "Beta", "P/E Ratio"
  title: string;
  body: string;
  tip: string;
  learnMoreUrl?: string;
}

export interface KeyDriver {
  feature: string;
  name: string;
  value: string;
  importance: number;
  explanation: string;
}

export interface LLMMetadata {
  enabled: boolean;
  used: boolean;
  model: string | null;
  fallback_reason?: string;
}

export interface AIExplanation {
  ticker: string;
  prediction: string;
  confidence: number;
  risk_score: number;
  risk_level: string;
  headline?: string;
  summary: string;
  trend_explanation: string;
  key_drivers: KeyDriver[];
  risk_explanation: string;
  watch_items: string[];
  llm?: LLMMetadata;
}
