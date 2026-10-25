import type { AuthUser, AuthResponse } from '@/types';

const _rawBase = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '');
const API_BASE = _rawBase.endsWith('/api') ? _rawBase.slice(0, -4) : _rawBase;

export interface SignUpData {
  username: string;
  email: string;
  name?: string;
  password: string;
}

export const authService = {
  async signup(data: SignUpData): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    const resData = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(resData.error || 'Failed to create account.');
    }

    return resData as AuthResponse;
  },

  async login(identifier: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, password }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || 'Authentication failed. Please check your credentials.');
    }

    return data as AuthResponse;
  },

  async logout(token?: string | null): Promise<void> {
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers,
      });
    } catch {
      // Ignore network errors on logout to allow local session clearing
    }
  },

  async getMe(token: string): Promise<AuthUser> {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || 'Session expired.');
    }

    return data.user as AuthUser;
  },
};
