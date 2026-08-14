import React, { useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { PricePoint, TimeRange } from '@/types';
import { formatCurrency, formatChartDate, changeClass } from '@/lib/utils';

const TIME_RANGES: TimeRange[] = ['1W', '1M', '3M', '6M', '1Y', '5Y'];

interface PriceChartPanelProps {
  ticker: string;
  data: PricePoint[];
  range: TimeRange;
  onRangeChange: (r: TimeRange) => void;
  isLoading?: boolean;
}

interface TooltipPayload {
  payload?: { date: string; close: number; volume: number }[];
  active?: boolean;
}

function CustomTooltip({ active, payload }: TooltipPayload): React.ReactElement | null {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div style={{
      background: 'var(--color-bg-elevated)',
      border: '1px solid var(--color-border-strong)',
      borderRadius: 'var(--radius-md)',
      padding: '10px 14px',
      boxShadow: 'var(--shadow-md)',
    }}>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 4 }}>
        {d.date}
      </div>
      <div style={{ fontSize: 'var(--font-size-base)', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>
        {formatCurrency(d.close)}
      </div>
    </div>
  );
}

export function PriceChartPanel({ ticker, data, range, onRangeChange, isLoading }: PriceChartPanelProps): React.ReactElement {
  const [hoveredRange, setHoveredRange] = useState<TimeRange | null>(null);

  const chartData = data.map(p => ({
    date: formatChartDate(p.date, range),
    close: p.close,
    volume: p.volume,
    rawDate: p.date,
  }));

  const firstClose = data[0]?.close ?? 0;
  const lastClose  = data[data.length - 1]?.close ?? 0;
  const isPositive = lastClose >= firstClose;
  const strokeColor = isPositive ? 'var(--color-gain)' : 'var(--color-loss)';
  const gradientId  = `chart-gradient-${ticker}`;

  const tickInterval = Math.max(1, Math.floor(chartData.length / 6));

  if (isLoading) {
    return (
      <div className="chart-panel">
        <div className="card__header">
          <div className="card__title">📉 Price History</div>
        </div>
        <div className="skeleton skeleton-chart" />
      </div>
    );
  }

  return (
    <div className="chart-panel">
      <div className="chart-panel__header">
        <div className="card__title">
          📉 Price History
          <span className={changeClass(lastClose - firstClose)} style={{ fontSize: 'var(--font-size-sm)', marginLeft: 8 }}>
            {isPositive ? '▲' : '▼'} {(((lastClose - firstClose) / firstClose) * 100).toFixed(2)}%
          </span>
        </div>
        <div className="time-range-selector" role="group" aria-label="Select time range">
          {TIME_RANGES.map(r => (
            <button
              key={r}
              className={`time-range-btn ${range === r ? 'time-range-btn--active' : ''} ${hoveredRange === r && range !== r ? 'time-range-btn--hover' : ''}`}
              onClick={() => onRangeChange(r)}
              onMouseEnter={() => setHoveredRange(r)}
              onMouseLeave={() => setHoveredRange(null)}
              aria-pressed={range === r}
              aria-label={`Show ${r} price history`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 8 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={isPositive ? 'hsl(142,70%,48%)' : 'hsl(0,75%,58%)'} stopOpacity={0.22} />
                <stop offset="95%" stopColor={isPositive ? 'hsl(142,70%,48%)' : 'hsl(0,75%,58%)'} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval={tickInterval}
            />
            <YAxis
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `$${v.toFixed(0)}`}
              width={52}
              domain={['auto', 'auto']}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="close"
              stroke={strokeColor}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              dot={false}
              activeDot={{ r: 4, fill: strokeColor, stroke: 'var(--color-bg-base)', strokeWidth: 2 }}
              animationDuration={800}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
