/**
 * analysisRoutes.js
 * ------------------
 * GET /api/analysis/:ticker
 */

import { Router } from 'express';
import { getAnalysis } from '../controllers/analysisController.js';

const router = Router();

// GET /api/analysis/:ticker
router.get('/:ticker', getAnalysis);

export default router;
