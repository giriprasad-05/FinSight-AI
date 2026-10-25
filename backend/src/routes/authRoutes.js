/**
 * authRoutes.js
 * -------------
 * Express router for authentication endpoints.
 */

import { Router } from 'express';
import { signup, login, logout, getMe } from '../controllers/authController.js';
import { requireAuth } from '../middleware/authMiddleware.js';

const router = Router();

router.post('/signup', signup);
router.post('/register', signup);
router.post('/login', login);
router.post('/logout', logout);
router.get('/me', requireAuth, getMe);

export default router;
