/**
 * chatRoutes.js
 * -------------
 * POST /api/chat
 */

import { Router } from 'express';
import { handleStockChat } from '../controllers/chatController.js';

const router = Router();

// POST /api/chat
router.post('/', handleStockChat);

export default router;
