/**
 * authMiddleware.js
 * -----------------
 * Middleware to protect routes and verify bearer tokens.
 */

import { verifyToken } from '../services/authService.js';

export function requireAuth(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      error: 'Unauthorized: Missing or invalid Authorization header.',
    });
  }

  const token = authHeader.slice(7).trim();
  const payload = verifyToken(token);

  if (!payload) {
    return res.status(401).json({
      error: 'Unauthorized: Invalid or expired token.',
    });
  }

  req.user = payload;
  next();
}

export function optionalAuth(req, res, next) {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.slice(7).trim();
    const payload = verifyToken(token);
    if (payload) {
      req.user = payload;
    }
  }
  next();
}
