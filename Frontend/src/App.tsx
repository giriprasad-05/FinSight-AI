import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from '@/components/layout/Navbar';
import { StockSearch } from '@/components/search/StockSearch';
import { HomePage } from '@/pages/Home/HomePage';
import { StockDashboard } from '@/pages/stock/StockDashboard';
import '@/styles/global.css';
import '@/styles/primitives.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App(): React.ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app-shell">
          <Navbar />
          <main className="app-main">
            <div className="search-container">
              <StockSearch />
            </div>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/stock/:ticker" element={<StockDashboard />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
