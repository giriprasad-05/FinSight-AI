import { create } from 'zustand';
import type { AuthUser } from '@/types';
import { authService, type SignUpData } from '@/services/authService';

const TOKEN_KEY = 'finsight_token';
const USER_KEY = 'finsight_user';

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  signup: (data: SignUpData) => Promise<void>;
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function getStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

const initialToken = getStoredToken();
const initialUser = getStoredUser();

export const useAuthStore = create<AuthState>((set, get) => ({
  token: initialToken,
  user: initialUser,
  isAuthenticated: Boolean(initialToken),
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  signup: async (data: SignUpData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.signup(data);
      localStorage.setItem(TOKEN_KEY, response.token);
      localStorage.setItem(USER_KEY, JSON.stringify(response.user));
      set({
        token: response.token,
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err: any) {
      set({
        isLoading: false,
        error: err.message || 'Account creation failed.',
      });
      throw err;
    }
  },

  login: async (identifier: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.login(identifier, password);
      localStorage.setItem(TOKEN_KEY, response.token);
      localStorage.setItem(USER_KEY, JSON.stringify(response.user));
      set({
        token: response.token,
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err: any) {
      set({
        isLoading: false,
        error: err.message || 'Login failed. Please verify credentials.',
      });
      throw err;
    }
  },

  logout: async () => {
    const currentToken = get().token;
    try {
      if (currentToken) {
        await authService.logout(currentToken);
      }
    } catch {
      // Continue cleanup regardless of network error
    } finally {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      set({
        token: null,
        user: null,
        isAuthenticated: false,
        error: null,
      });
    }
  },

  checkAuth: async () => {
    const token = get().token;
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    try {
      const user = await authService.getMe(token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      set({ user, isAuthenticated: true });
    } catch {
      // Token is expired, revoked, or user reset
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      set({ token: null, user: null, isAuthenticated: false });
    }
  },
}));
