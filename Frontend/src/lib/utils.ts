// ── Formatting utilities ───────────────────────────────────────

/** Format a number as USD currency */
export function formatCurrency(value: number, compact = false): string {
  const safeValue = value ?? 0;
  if (compact) {
    if (Math.abs(safeValue) >= 1e12) return `$${(safeValue / 1e12).toFixed(2)}T`;
    if (Math.abs(safeValue) >= 1e9)  return `$${(safeValue / 1e9).toFixed(2)}B`;
    if (Math.abs(safeValue) >= 1e6)  return `$${(safeValue / 1e6).toFixed(2)}M`;
    if (Math.abs(safeValue) >= 1e3)  return `$${(safeValue / 1e3).toFixed(1)}K`;
    return `$${safeValue.toFixed(2)}`;
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(safeValue);
}

/** Format a number as percentage with sign */
export function formatPercent(value: number, includeSign = true): string {
  const safeValue = value ?? 0;
  const sign = includeSign && safeValue > 0 ? '+' : '';
  return `${sign}${safeValue.toFixed(2)}%`;
}

/** Format large numbers with commas */
export function formatNumber(value: number): string {
  const safeValue = value ?? 0;
  return new Intl.NumberFormat('en-US').format(safeValue);
}

/** Format volume (e.g. 54.3M) */
export function formatVolume(value: number): string {
  const safeValue = value ?? 0;
  if (safeValue >= 1e9) return `${(safeValue / 1e9).toFixed(1)}B`;
  if (safeValue >= 1e6) return `${(safeValue / 1e6).toFixed(1)}M`;
  if (safeValue >= 1e3) return `${(safeValue / 1e3).toFixed(0)}K`;
  return safeValue.toString();
}

/** Determine gain/loss class name */
export function changeClass(value: number): string {
  if (value > 0) return 'text-gain';
  if (value < 0) return 'text-loss';
  return 'text-muted';
}

/** Get badge variant from price change */
export function changeBadge(value: number): 'gain' | 'loss' | 'neutral' {
  if (value > 0) return 'gain';
  if (value < 0) return 'loss';
  return 'neutral';
}

/** Clamp a value between min and max */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** Join class names, filtering falsy values */
export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}

/** Format date string for chart axis */
export function formatChartDate(dateStr: string, range: string): string {
  const date = new Date(dateStr);
  if (range === '1W') {
    return date.toLocaleDateString('en-US', { weekday: 'short' });
  }
  if (range === '1M' || range === '3M') {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
  return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
}

/** Get risk level color token */
export function riskColor(level: string): string {
  const map: Record<string, string> = {
    Low:       'var(--color-risk-low)',
    Medium:    'var(--color-risk-medium)',
    High:      'var(--color-risk-high)',
    'Very High':'var(--color-risk-very-high)',
  };
  return map[level] ?? 'var(--color-neutral)';
}

/** Get trend direction color */
export function trendColor(direction: string): string {
  const map: Record<string, string> = {
    Bullish:  'var(--color-gain)',
    Bearish:  'var(--color-loss)',
    Neutral:  'var(--color-neutral)',
    Volatile: 'var(--color-warning)',
  };
  return map[direction] ?? 'var(--color-neutral)';
}
