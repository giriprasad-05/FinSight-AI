/**
 * errorHandler.js
 * ----------------
 * Centralised Express error-handling middleware.
 *
 * Must be registered LAST with app.use() so that errors thrown
 * or next(err)'d by any route/controller land here.
 *
 * Rules:
 *   - Never expose stack traces in production.
 *   - Map known statusCode properties to proper HTTP codes.
 *   - Always return JSON with a consistent shape.
 */

const isDev = process.env.NODE_ENV !== 'production';

/**
 * @param {Error} err
 * @param {import('express').Request} req
 * @param {import('express').Response} res
 * @param {import('express').NextFunction} _next
 */
export function errorHandler(err, req, res, _next) {
  // Determine HTTP status code
  const status =
    typeof err.statusCode === 'number' && err.statusCode >= 100
      ? err.statusCode
      : 500;

  // Build the response body
  const body = {
    error: err.message || 'Internal server error',
    status,
    path: req.originalUrl,
  };

  // Include stack only in development
  if (isDev && err.stack) {
    body.stack = err.stack;
  }

  res.status(status).json(body);
}

/**
 * 404 handler — register BEFORE errorHandler, AFTER all routes.
 *
 * @param {import('express').Request} req
 * @param {import('express').Response} res
 */
export function notFoundHandler(req, res) {
  res.status(404).json({
    error: `Route not found: ${req.method} ${req.originalUrl}`,
    status: 404,
  });
}
