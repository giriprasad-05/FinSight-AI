import React from 'react';
import { Navigate } from 'react-router-dom';

export function HomePage(): React.ReactElement {
  // Default to AAPL to immediately show the dashboard rather than an empty page
  return <Navigate to="/stock/AAPL" replace />;
}
