import type { TimeRange } from '@/types';

// ── TanStack Query key factory ────────────────────────────────
// Using factory pattern ensures consistent, refetchable query keys
// across all hooks. When the ticker changes, all keys auto-invalidate.
export const queryKeys = {
  stocks: {
    all: ['stocks'] as const,
    search: (query: string) => ['stocks', 'search', query] as const,
    detail: (ticker: string) => ['stocks', 'detail', ticker] as const,
    priceHistory: (ticker: string, range: TimeRange) =>
      ['stocks', 'priceHistory', ticker, range] as const,
  },
  risk: {
    all: ['risk'] as const,
    assessment: (ticker: string) => ['risk', 'assessment', ticker] as const,
    trend: (ticker: string) => ['risk', 'trend', ticker] as const,
  },
  education: {
    insight: (ticker: string) => ['education', 'insight', ticker] as const,
  },
} as const;
