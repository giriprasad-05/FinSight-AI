/**
 * authService.js
 * --------------
 * Authentication service for FinSight AI.
 *
 * Implements:
 *   - Secure password hashing and verification using Node.js native crypto (scrypt + timingSafeEqual)
 *   - Secure HMAC-SHA256 token generation and verification (zero external dependencies)
 *   - User registration (Sign Up) with input validation and persistence
 *   - User authentication (Login)
 *   - Token revocation for explicit logout
 *   - Persistent user store in data/users.json (plain-text passwords are NEVER stored)
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const USERS_FILE = path.resolve(__dirname, '../data/users.json');

// Secret key for HMAC token signing (can be overridden via environment variable)
const AUTH_SECRET = process.env.AUTH_SECRET || 'finsight-ai-jwt-auth-secret-key-2026';
const TOKEN_TTL_SECONDS = 24 * 60 * 60; // 24 hours

/**
 * Hash a password using scrypt with a random or provided salt.
 * Returns { salt, hash }.
 */
export function hashPassword(password, existingSalt = null) {
  const salt = existingSalt || crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 64).toString('hex');
  return { salt, hash };
}

/**
 * Verify a plain password against a stored salt and hash using timingSafeEqual.
 */
export function verifyPassword(password, salt, storedHash) {
  try {
    const candidateHash = crypto.scryptSync(password, salt, 64);
    const expectedHash = Buffer.from(storedHash, 'hex');
    if (candidateHash.length !== expectedHash.length) {
      return false;
    }
    return crypto.timingSafeEqual(candidateHash, expectedHash);
  } catch {
    return false;
  }
}

// ── Persistent User Store ──────────────────────────────────────────
function loadUsers() {
  try {
    if (fs.existsSync(USERS_FILE)) {
      const data = fs.readFileSync(USERS_FILE, 'utf8');
      return JSON.parse(data || '[]');
    }
  } catch (err) {
    console.error('[authService] Error loading users.json:', err.message);
  }
  return [];
}

function saveUsers(usersList) {
  try {
    const dir = path.dirname(USERS_FILE);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(USERS_FILE, JSON.stringify(usersList, null, 2), 'utf8');
  } catch (err) {
    console.error('[authService] Error saving users.json:', err.message);
  }
}

let users = loadUsers();

/**
 * Register a new user with validation.
 */
export function registerUser({ username, email, name, password }) {
  const normalizedUsername = (username || '').trim().toLowerCase();
  const normalizedEmail = (email || '').trim().toLowerCase();
  const displayName = (name || '').trim() || normalizedUsername;

  if (!normalizedUsername || normalizedUsername.length < 3) {
    throw new Error('Username must be at least 3 characters long.');
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(normalizedUsername)) {
    throw new Error('Username can only contain letters, numbers, underscores, and hyphens.');
  }

  if (!normalizedEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
    throw new Error('Please enter a valid email address.');
  }

  if (!password || password.length < 6) {
    throw new Error('Password must be at least 6 characters long.');
  }

  // Reload to ensure fresh state
  users = loadUsers();

  const existing = users.find(
    (u) => u.username === normalizedUsername || u.email === normalizedEmail
  );

  if (existing) {
    if (existing.username === normalizedUsername) {
      throw new Error('This username is already taken. Please choose another.');
    }
    throw new Error('An account with this email already exists.');
  }

  const { salt, hash } = hashPassword(password);
  const newUser = {
    id: `user_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`,
    username: normalizedUsername,
    email: normalizedEmail,
    name: displayName,
    salt,
    passwordHash: hash,
    createdAt: new Date().toISOString(),
  };

  users.push(newUser);
  saveUsers(users);

  const { token, expiresIn } = generateToken(newUser);

  return {
    token,
    expiresIn,
    user: {
      id: newUser.id,
      username: newUser.username,
      email: newUser.email,
      name: newUser.name,
    },
  };
}

// ── Token Revocation Set ──────────────────────────────────────────
const revokedTokens = new Map(); // token -> expiryTimestamp

function cleanExpiredRevocations() {
  const now = Date.now();
  for (const [token, expiry] of revokedTokens.entries()) {
    if (expiry <= now) {
      revokedTokens.delete(token);
    }
  }
}

// ── Native Token Handling (HMAC-SHA256 JWT) ───────────────────────
function base64UrlEncode(str) {
  return Buffer.from(str)
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}

function base64UrlDecode(str) {
  str = str.replace(/-/g, '+').replace(/_/g, '/');
  while (str.length % 4) {
    str += '=';
  }
  return Buffer.from(str, 'base64').toString('utf8');
}

export function generateToken(user) {
  const header = {
    alg: 'HS256',
    typ: 'JWT',
  };

  const now = Math.floor(Date.now() / 1000);
  const payload = {
    sub: user.id,
    username: user.username,
    email: user.email,
    name: user.name,
    iat: now,
    exp: now + TOKEN_TTL_SECONDS,
  };

  const encodedHeader = base64UrlEncode(JSON.stringify(header));
  const encodedPayload = base64UrlEncode(JSON.stringify(payload));
  const data = `${encodedHeader}.${encodedPayload}`;

  const signature = crypto
    .createHmac('sha256', AUTH_SECRET)
    .update(data)
    .digest('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');

  return {
    token: `${data}.${signature}`,
    expiresIn: TOKEN_TTL_SECONDS,
  };
}

export function verifyToken(token) {
  cleanExpiredRevocations();

  if (!token || typeof token !== 'string') {
    return null;
  }

  if (revokedTokens.has(token)) {
    return null;
  }

  const parts = token.split('.');
  if (parts.length !== 3) {
    return null;
  }

  const [encodedHeader, encodedPayload, signature] = parts;
  const data = `${encodedHeader}.${encodedPayload}`;

  const expectedSignature = crypto
    .createHmac('sha256', AUTH_SECRET)
    .update(data)
    .digest('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');

  // Verify signature with timing-safe comparison
  const sigBuf = Buffer.from(signature);
  const expBuf = Buffer.from(expectedSignature);
  if (sigBuf.length !== expBuf.length || !crypto.timingSafeEqual(sigBuf, expBuf)) {
    return null;
  }

  try {
    const payload = JSON.parse(base64UrlDecode(encodedPayload));
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < now) {
      return null;
    }
    return payload;
  } catch {
    return null;
  }
}

export function revokeToken(token) {
  try {
    const payload = verifyToken(token);
    const expiry = payload?.exp ? payload.exp * 1000 : Date.now() + TOKEN_TTL_SECONDS * 1000;
    revokedTokens.set(token, expiry);
    return true;
  } catch {
    return false;
  }
}

export function findUserByIdentifier(identifier) {
  if (!identifier) return null;
  const normalized = identifier.trim().toLowerCase();
  users = loadUsers();
  return users.find(
    (u) => u.username === normalized || u.email === normalized
  ) || null;
}

export function findUserById(id) {
  users = loadUsers();
  return users.find((u) => u.id === id) || null;
}
