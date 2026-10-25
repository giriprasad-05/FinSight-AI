/**
 * riskRoutes.js
 * --------------
 * GET /api/risk/:ticker
 */

import { Router } from 'express';
import { getRisk } from '../controllers/riskController.js';

const router = Router();

// GET /api/risk/:ticker
router.get('/:ticker', getRisk);

export default router;
