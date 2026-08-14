import { create } from 'zustand';
import type { StockMeta, TimeRange } from '@/types';

interface StockState {
  // ── Selected stock ──────────────────────────────────────────
  selectedTicker: string | null;
  selectedStockMeta: StockMeta | null;

  // ── Time range for chart ────────────────────────────────────
  timeRange: TimeRange;

  // ── Search ──────────────────────────────────────────────────
  searchQuery: string;
  searchResults: StockMeta[];
  isSearchOpen: boolean;

  // ── Actions ─────────────────────────────────────────────────
  selectStock: (ticker: string, meta?: StockMeta) => void;
  clearSelection: () => void;
  setTimeRange: (range: TimeRange) => void;
  setSearchQuery: (query: string) => void;
  setSearchResults: (results: StockMeta[]) => void;
  openSearch: () => void;
  closeSearch: () => void;
}

export const useStockStore = create<StockState>((set) => ({
  selectedTicker: null,
  selectedStockMeta: null,
  timeRange: '3M',
  searchQuery: '',
  searchResults: [],
  isSearchOpen: false,

  selectStock: (ticker, meta) =>
    set({
      selectedTicker: ticker.toUpperCase(),
      selectedStockMeta: meta ?? null,
      isSearchOpen: false,
      searchQuery: '',
    }),

  clearSelection: () =>
    set({
      selectedTicker: null,
      selectedStockMeta: null,
    }),

  setTimeRange: (range) => set({ timeRange: range }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSearchResults: (results) => set({ searchResults: results }),
  openSearch: () => set({ isSearchOpen: true }),
  closeSearch: () => set({ isSearchOpen: false, searchQuery: '', searchResults: [] }),
}));
