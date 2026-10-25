import React, { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Navbar } from '@/components/layout/Navbar';
import { StockSearch } from '@/components/search/StockSearch';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { LoginPage } from '@/pages/auth/LoginPage';
import { AboutPage } from '@/pages/About/AboutPage';
import { HomePage } from '@/pages/Home/HomePage';
import { StockDashboard } from '@/pages/stock/StockDashboard';
import { useAuthStore } from '@/store/authStore';
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

function AppShell(): React.ReactElement {
  const location = useLocation();
  const checkAuth = useAuthStore((s) => s.checkAuth);
  const isLoginPage = location.pathname === '/login';

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <div className="app-shell">
      <Navbar />
      <main className="app-main">
        {!isLoginPage && (
          <div className="search-container">
            <StockSearch />
          </div>
        )}
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <HomePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/stock/:ticker"
            element={
              <ProtectedRoute>
                <StockDashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function App(): React.ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
