import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X } from 'lucide-react';
import { useStockStore } from '@/store/stockStore';
import { useStockSearch } from '@/hooks/useStockData';

interface StockSearchProps {
  placeholder?: string;
}

export function StockSearch({ placeholder }: StockSearchProps): React.ReactElement {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const selectStock = useStockStore(s => s.selectStock);

  // Debounce search input (250ms) to avoid excessive queries while typing
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchTerm.trim());
    }, 250);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  // Query backend search API (returns all 35 stocks on empty query, or filtered results)
  const { data: searchResults, isLoading, isError } = useStockSearch(debouncedQuery);

  const handleSelect = useCallback((ticker: string) => {
    selectStock(ticker);
    setSearchTerm('');
    setDebouncedQuery('');
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

  const results = useMemo(() => searchResults ?? [], [searchResults]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      setSearchTerm('');
      setDebouncedQuery('');
    }
    if (e.key === 'Enter' && results.length > 0) {
      handleSelect(results[0].ticker);
    }
  }, [results, handleSelect]);

  // When query is empty, group all 35 supported stocks by market (United States & India)
  const isUniverseView = debouncedQuery === '';
  const usStocks = useMemo(
    () => results.filter(s => s.country === 'United States' || !s.ticker.endsWith('.NS')),
    [results]
  );
  const indiaStocks = useMemo(
    () => results.filter(s => s.country === 'India' || s.ticker.endsWith('.NS')),
    [results]
  );

  return (
    <div className="stock-search">
      <div className="input-wrap">
        <Search size={16} className="stock-search__icon" />
        <input
          ref={inputRef}
          type="text"
          className="stock-search__input"
          placeholder={placeholder ?? 'Search all 35 stocks (e.g., AAPL, RELIANCE, TCS, NVDA)'}
          value={searchTerm}
          onChange={e => {
            setSearchTerm(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          spellCheck={false}
        />
        {searchTerm && (
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
              setSearchTerm('');
              setDebouncedQuery('');
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
            <div className="stock-search__status">
              Searching...
            </div>
          )}

          {isError && (
            <div className="stock-search__status stock-search__status--error">
              Unable to search stocks.
            </div>
          )}

          {!isLoading && !isError && results.length === 0 && (
            <div className="stock-search__status">
              No supported stocks found.
            </div>
          )}

          {!isLoading && !isError && results.length > 0 && (
            <>
              {isUniverseView ? (
                <>
                  {usStocks.length > 0 && (
                    <>
                      <div className="stock-search__group-header">
                        United States ({usStocks.length})
                      </div>
                      {usStocks.map(s => (
                        <button
                          key={s.ticker}
                          type="button"
                          className="stock-search__item"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            handleSelect(s.ticker);
                          }}
                          onClick={() => handleSelect(s.ticker)}
                        >
                          <span className="stock-search__ticker">{s.ticker}</span>
                          <span className="stock-search__name">{s.name}</span>
                          <span className="stock-search__market">US</span>
                        </button>
                      ))}
                    </>
                  )}

                  {indiaStocks.length > 0 && (
                    <>
                      <div className="stock-search__group-header">
                        India / NSE ({indiaStocks.length})
                      </div>
                      {indiaStocks.map(s => (
                        <button
                          key={s.ticker}
                          type="button"
                          className="stock-search__item"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            handleSelect(s.ticker);
                          }}
                          onClick={() => handleSelect(s.ticker)}
                        >
                          <span className="stock-search__ticker">{s.ticker}</span>
                          <span className="stock-search__name">{s.name}</span>
                          <span className="stock-search__market">India</span>
                        </button>
                      ))}
                    </>
                  )}
                </>
              ) : (
                results.map(s => (
                  <button
                    key={s.ticker}
                    type="button"
                    className="stock-search__item"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleSelect(s.ticker);
                    }}
                    onClick={() => handleSelect(s.ticker)}
                  >
                    <span className="stock-search__ticker">{s.ticker}</span>
                    <span className="stock-search__name">{s.name}</span>
                    <span className="stock-search__market">
                      {s.country === 'India' || s.ticker.endsWith('.NS') ? 'India' : 'US'}
                    </span>
                  </button>
                ))
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
