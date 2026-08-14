import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X } from 'lucide-react';
import { useStockStore } from '@/store/stockStore';
import { useStockSearch } from '@/hooks/useStockData';
import { MOCK_STOCK_LIST } from '@/data/stocks';

interface StockSearchProps {
  placeholder?: string;
}

export function StockSearch({ placeholder }: StockSearchProps): React.ReactElement {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const selectStock = useStockStore(s => s.selectStock);

  const { data: searchResults, isLoading } = useStockSearch(query);
  const displayResults = query.length > 0 ? (searchResults ?? []) : MOCK_STOCK_LIST.slice(0, 8);

  const handleSelect = useCallback((ticker: string) => {
    const meta = MOCK_STOCK_LIST.find(s => s.ticker === ticker);
    selectStock(ticker, meta);
    setQuery('');
    setIsOpen(false);
    navigate(`/stock/${ticker}`);
  }, [navigate, selectStock]);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (
        dropdownRef.current && !dropdownRef.current.contains(e.target as Node) &&
        !inputRef.current?.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      setQuery('');
    }
    if (e.key === 'Enter' && displayResults.length > 0) {
      handleSelect(displayResults[0].ticker);
    }
  }, [displayResults, handleSelect]);

  return (
    <div className="stock-search">
      <div className="input-wrap">
        <Search size={16} className="stock-search__icon" />
        <input
          ref={inputRef}
          type="text"
          className="stock-search__input"
          placeholder={placeholder ?? 'Search stocks (e.g., AAPL, Apple Inc., NVDA, MSFT)'}
          value={query}
          onChange={e => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          spellCheck={false}
        />
        {query && (
          <button
            type="button"
            aria-label="Clear search"
            style={{
              position: 'absolute',
              right: '16px',
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'none',
              border: 'none',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '4px',
            }}
            onClick={() => {
              setQuery('');
              inputRef.current?.focus();
            }}
          >
            <X size={15} />
          </button>
        )}
      </div>

      {isOpen && (
        <div ref={dropdownRef} className="stock-search__dropdown">
          {isLoading && (
            <div style={{ padding: 'var(--space-3) var(--space-4)', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
              Searching…
            </div>
          )}
          {!isLoading && displayResults.length === 0 && (
            <div style={{ padding: 'var(--space-4)', color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', textAlign: 'center' }}>
              No results for "{query}"
            </div>
          )}
          {!isLoading && displayResults.map(s => (
            <button
              key={s.ticker}
              type="button"
              className="stock-search__item"
              onClick={() => handleSelect(s.ticker)}
            >
              <span className="stock-search__ticker">{s.ticker}</span>
              <span className="stock-search__name">{s.name}</span>
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-sans)' }}>
                {s.sector}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
