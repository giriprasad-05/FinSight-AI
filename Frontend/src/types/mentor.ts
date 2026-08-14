// ── AI Mentor / Chat types ───────────────────────────────────

export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;          // ISO timestamp
}

export interface MentorContext {
  ticker: string;
  companyName: string;
  riskLevel: string;
  riskScore: number;
  trendDirection: string;
  price: number;
  priceChangePct: number;
}

export interface QuickPrompt {
  id: string;
  label: string;
  prompt: string;
}
