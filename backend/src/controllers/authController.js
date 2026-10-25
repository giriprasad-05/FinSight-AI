/**
 * authController.js
 * -----------------
 * Handles signup (registration), login, logout, and token session verification endpoints.
 */

import {
  registerUser,
  findUserByIdentifier,
  findUserById,
  verifyPassword,
  generateToken,
  revokeToken,
} from '../services/authService.js';

export async function signup(req, res, next) {
  try {
    const { username, email, name, password } = req.body || {};

    if (!username || !email || !password) {
      return res.status(400).json({
        error: 'Username, email, and password are required.',
      });
    }

    const result = registerUser({ username, email, name, password });
    return res.status(201).json(result);
  } catch (err) {
    return res.status(400).json({
      error: err.message || 'Registration failed.',
    });
  }
}

export async function login(req, res, next) {
  try {
    const { identifier, email, username, password } = req.body || {};
    const candidateIdentifier = identifier || email || username;

    if (!candidateIdentifier || !password) {
      return res.status(400).json({
        error: 'Email/username and password are required.',
      });
    }

    const user = findUserByIdentifier(candidateIdentifier);
    if (!user) {
      return res.status(401).json({
        error: 'Invalid email/username or password.',
      });
    }

    const isMatch = verifyPassword(password, user.salt, user.passwordHash);
    if (!isMatch) {
      return res.status(401).json({
        error: 'Invalid email/username or password.',
      });
    }

    const { token, expiresIn } = generateToken(user);

    return res.status(200).json({
      token,
      expiresIn,
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        name: user.name,
      },
    });
  } catch (err) {
    next(err);
  }
}

export async function logout(req, res, next) {
  try {
    const authHeader = req.headers.authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      const token = authHeader.slice(7).trim();
      revokeToken(token);
    }

    return res.status(200).json({
      message: 'Logged out successfully.',
    });
  } catch (err) {
    next(err);
  }
}

export async function getMe(req, res, next) {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Not authenticated.' });
    }

    const user = findUserById(req.user.sub || req.user.id);
    if (!user) {
      return res.status(404).json({ error: 'User not found.' });
    }

    return res.status(200).json({
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        name: user.name,
      },
    });
  } catch (err) {
    next(err);
  }
}
