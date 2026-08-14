import { useQuery } from '@tanstack/react-query';
import { useStockStore } from '@/store/stockStore';
import { stockService } from '@/services';
import { queryKeys } from '@/lib/queryKeys';
import type { TimeRange } from '@/types';

export function useSelectedStock() {
  return useStockStore((s) => ({
    ticker: s.selectedTicker,
    meta: s.selectedStockMeta,
    timeRange: s.timeRange,
    selectStock: s.selectStock,
    setTimeRange: s.setTimeRange,
  }));
}

export function useStockDetail(ticker: string | null) {
  return useQuery({
    queryKey: queryKeys.stocks.detail(ticker ?? ''),
    queryFn: () => stockService.getStock(ticker!),
    enabled: !!ticker,
    staleTime: 5 * 60 * 1000,   // 5 min
    gcTime: 10 * 60 * 1000,     // 10 min
  });
}

export function usePriceHistory(ticker: string | null, range: TimeRange) {
  return useQuery({
    queryKey: queryKeys.stocks.priceHistory(ticker ?? '', range),
    queryFn: () => stockService.getPriceHistory(ticker!, range),
    enabled: !!ticker,
    staleTime: 2 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
  });
}

export function useRiskAssessment(ticker: string | null) {
  return useQuery({
    queryKey: queryKeys.risk.assessment(ticker ?? ''),
    queryFn: () => stockService.getRiskAssessment(ticker!),
    enabled: !!ticker,
    staleTime: 10 * 60 * 1000,
    gcTime: 20 * 60 * 1000,
  });
}

export function useTrendAnalysis(ticker: string | null) {
  return useQuery({
    queryKey: queryKeys.risk.trend(ticker ?? ''),
    queryFn: () => stockService.getTrendAnalysis(ticker!),
    enabled: !!ticker,
    staleTime: 10 * 60 * 1000,
    gcTime: 20 * 60 * 1000,
  });
}

export function useEducationalInsight(ticker: string | null) {
  return useQuery({
    queryKey: queryKeys.education.insight(ticker ?? ''),
    queryFn: () => stockService.getEducationalInsight(ticker!),
    enabled: !!ticker,
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}

export function useStockSearch(query: string) {
  return useQuery({
    queryKey: queryKeys.stocks.search(query),
    queryFn: () => stockService.searchStocks(query),
    enabled: query.length > 0,
    staleTime: 30 * 1000,
  });
}
