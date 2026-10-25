/**
 * server.js
 * ----------
 * HTTP server entry point.
 *
 * Imports the Express app, binds it to PORT, and handles graceful shutdown.
 * Kept intentionally thin — all middleware/routing lives in app.js.
 */

import 'dotenv/config';
import app from './app.js';

const PORT = parseInt(process.env.PORT || '5000', 10);
const HOST = process.env.HOST;

function onListening() {
  console.log(`\n🚀 FinSight AI Backend`);
  console.log(`   Listening on http://${HOST || 'localhost'}:${PORT}`);
  console.log(`   Environment  : ${process.env.NODE_ENV || 'development'}`);
  console.log(`   ML service   : ${process.env.ML_SERVICE_URL || 'http://127.0.0.1:8000'}`);
  console.log(`   Frontend URL : ${process.env.FRONTEND_URL || 'http://localhost:5173'}`);
  console.log(`\n   Endpoints:`);
  console.log(`     GET  /api/health`);
  console.log(`     POST /api/auth/signup`);
  console.log(`     POST /api/auth/login`);
  console.log(`     POST /api/auth/logout`);
  console.log(`     GET  /api/auth/me`);
  console.log(`     GET  /api/stocks/:ticker`);
  console.log(`     GET  /api/stocks/:ticker/quote`);
  console.log(`     GET  /api/predictions/:ticker`);
  console.log(`     GET  /api/risk/:ticker`);
  console.log(`     GET  /api/analysis/:ticker\n`);
}

const server = HOST
  ? app.listen(PORT, HOST, onListening)
  : app.listen(PORT, onListening);

// ── Graceful shutdown ─────────────────────────────────────────────
function shutdown(signal) {
  console.log(`\n[server] Received ${signal}. Shutting down gracefully…`);
  server.close(() => {
    console.log('[server] HTTP server closed.');
    process.exit(0);
  });

  // Force exit if shutdown takes too long
  setTimeout(() => {
    console.error('[server] Forced exit after timeout.');
    process.exit(1);
  }, 10_000);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

// Unhandled rejection safety net
process.on('unhandledRejection', (reason) => {
  console.error('[server] Unhandled rejection:', reason);
});
