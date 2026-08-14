import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { PricePoint, TimeRange } from '@/types';
import { formatCurrency, formatChartDate } from '@/lib/utils';
import { format } from 'date-fns';

const TIME_RANGES: TimeRange[] = ['1W', '1M', '3M', '6M', '1Y', '5Y'];

interface PriceChartProps {
  data: PricePoint[];
  range: TimeRange;
  onRangeChange: (r: TimeRange) => void;
  isLoading?: boolean;
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{ payload: { rawDate: string; close: number } }>;
}

function ChartTooltip({ active, payload }: TooltipProps): React.ReactElement | null {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  
  // Format the date properly for the tooltip
  const parsedDate = new Date(d.rawDate);
  const displayDate = isNaN(parsedDate.getTime()) ? d.rawDate : format(parsedDate, 'MMM d, yyyy');

  return (
    <div style={{
      background: 'var(--color-bg-base)',
      border: '1px solid var(--color-border)',
      borderRadius: '8px',
      padding: '8px 12px',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
      textAlign: 'center'
    }}>
      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-primary)', marginBottom: '4px' }}>
        {displayDate}
      </div>
      <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
        Close: {formatCurrency(d.close)}
      </div>
    </div>
  );
}

export function PriceChart({ data, range, onRangeChange, isLoading }: PriceChartProps): React.ReactElement {
  const chartData = data.map(p => ({
    date: formatChartDate(p.date, range),
    close: p.close,
    rawDate: p.date,
  }));

  const tickInterval = Math.max(1, Math.floor(chartData.length / 5));

  if (isLoading) {
    return (
      <div className="card chart-card">
        <div className="chart-header">
          <span className="chart-title">Historical Price</span>
        </div>
        <div className="skeleton skeleton-chart skeleton-block" style={{ height: '240px' }} />
      </div>
    );
  }

  return (
    <div className="card chart-card">
      <div className="chart-header">
        <span className="chart-title">Historical Price</span>
      </div>
      
      <div className="chart-controls" style={{ marginLeft: 0, marginBottom: 'var(--space-4)' }}>
        {TIME_RANGES.map(r => (
          <button
            key={r}
            className={`timeframe-btn${range === r ? ' timeframe-btn--active' : ''}`}
            onClick={() => onRangeChange(r)}
          >
            {r}
          </button>
        ))}
      </div>

      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 20, right: 10, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-accent)" stopOpacity={0.1}/>
                <stop offset="95%" stopColor="var(--color-accent)" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" />
            <XAxis
              dataKey="date"
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval={tickInterval}
              dy={10}
            />
            <YAxis
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => v.toFixed(0)}
              width={40}
              domain={['auto', 'auto']}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'var(--color-border)', strokeWidth: 1, strokeDasharray: '3 3' }} />
            <Area
              type="monotone"
              dataKey="close"
              stroke="var(--color-accent)"
              strokeWidth={2}
              fill="url(#colorClose)"
              dot={{ r: 3, fill: 'var(--color-accent)', strokeWidth: 0 }}
              activeDot={{ r: 5, fill: 'var(--color-accent)', stroke: 'var(--color-bg-base)', strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
