/**
 * explainRoutes.js
 * ----------------
 * GET /api/explain/:ticker
 */

import { Router } from 'express';
import { getExplanation } from '../controllers/explainController.js';

const router = Router();

// GET /api/explain/:ticker
router.get('/:ticker', getExplanation);

export default router;
