/**
 * predictionRoutes.js
 * --------------------
 * GET /api/predictions/:ticker
 */

import { Router } from 'express';
import { getPrediction } from '../controllers/predictionController.js';

const router = Router();

// GET /api/predictions/:ticker
router.get('/:ticker', getPrediction);

export default router;
