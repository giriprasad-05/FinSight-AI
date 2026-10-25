/**
 * app.js
 * -------
 * Express application factory.
 *
 * Sets up:
 *   - Security headers (helmet)
 *   - Request logging (morgan)
 *   - CORS (configured via FRONTEND_URL env var)
 *   - Rate limiting
 *   - JSON body parsing
 *   - All API routes
 *   - 404 and error handlers
 *
 * Exported as a function so server.js can import it, and tests can
 * mount it without binding to a port.
 */

import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';

import stockRoutes from './routes/stockRoutes.js';
import predictionRoutes from './routes/predictionRoutes.js';
import riskRoutes from './routes/riskRoutes.js';
import analysisRoutes from './routes/analysisRoutes.js';
import explainRoutes from './routes/explainRoutes.js';
import chatRoutes from './routes/chatRoutes.js';
import authRoutes from './routes/authRoutes.js';
import { getMlHealth } from './services/stockService.js';
import { notFoundHandler, errorHandler } from './middleware/errorHandler.js';

// ── CORS origins ──────────────────────────────────────────────────
// Accept comma-separated list in FRONTEND_URL to support multiple dev origins.
const allowedOrigins = (process.env.FRONTEND_URL || 'http://localhost:5173,http://127.0.0.1:5173')
  .split(',')
  .map((o) => o.trim())
  .filter(Boolean);

const corsOptions = {
  origin(origin, callback) {
    // Allow requests with no origin (curl, Postman, server-to-server)
    if (!origin) return callback(null, true);
    if (
      allowedOrigins.includes(origin) ||
      /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)
    ) {
      return callback(null, true);
    }
    callback(new Error(`CORS: origin "${origin}" not allowed.`));
  },
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  optionsSuccessStatus: 200,
};

// ── Rate limiter ──────────────────────────────────────────────────
const apiLimiter = rateLimit({
  windowMs: 60 * 1000,   // 1 minute
  max: 300,              // 300 requests per minute per IP
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests. Please wait a moment.', status: 429 },
});

// ── App factory ───────────────────────────────────────────────────
const app = express();

// Security headers
app.use(helmet());

// CORS
app.use(cors(corsOptions));
app.options('*', cors(corsOptions)); // pre-flight

// Request logging (compact in production, colored dev format in development)
app.use(morgan(process.env.NODE_ENV === 'production' ? 'combined' : 'dev'));

// Body parsing
app.use(express.json());

// Rate limiting (apply to all /api routes)
app.use('/api', apiLimiter);

// ── Health check ──────────────────────────────────────────────────
/**
 * GET /api/health
 *
 * Returns Node backend status + Python ML service status.
 */
app.get('/api/health', async (req, res) => {
  const nodeHealth = {
    status: 'ok',
    service: 'FinSight AI Node Backend',
    version: '1.0.0',
    environment: process.env.NODE_ENV || 'development',
    timestamp: new Date().toISOString(),
  };

  // Also probe the Python ML service
  try {
    const mlHealth = await getMlHealth();
    res.json({
      ...nodeHealth,
      ml_service: { status: 'ok', ...mlHealth },
    });
  } catch (err) {
    // Node is healthy even if ML service is down — report both
    res.status(207).json({
      ...nodeHealth,
      ml_service: {
        status: 'unavailable',
        error: err.message,
      },
    });
  }
});

// ── API routes ────────────────────────────────────────────────────
app.use('/api/auth', authRoutes);
app.use('/api/stocks', stockRoutes);
app.use('/api/predictions', predictionRoutes);
app.use('/api/risk', riskRoutes);
app.use('/api/analysis', analysisRoutes);
app.use('/api/explain', explainRoutes);
app.use('/api/chat', chatRoutes);

// ── 404 + error handlers (must be LAST) ──────────────────────────
app.use(notFoundHandler);
app.use(errorHandler);

export default app;
