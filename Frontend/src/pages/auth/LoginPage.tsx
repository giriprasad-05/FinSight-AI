import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import {
  Lock,
  Mail,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  ShieldCheck,
  UserPlus,
  LogIn,
} from 'lucide-react';
import './LoginPage.css';

type AuthMode = 'login' | 'signup';

export function LoginPage(): React.ReactElement {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, signup, isLoading, error, clearError, isAuthenticated } = useAuthStore();

  const [mode, setMode] = useState<AuthMode>('login');

  // Login form state
  const [identifier, setIdentifier] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Sign up form state
  const [name, setName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Password visibility
  const [showPassword, setShowPassword] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Destination path if redirected
  const from = (location.state as { from?: { pathname?: string } })?.from?.pathname || '/';

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const handleTabChange = (newMode: AuthMode) => {
    setMode(newMode);
    clearError();
    setValidationError(null);
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    if (!identifier.trim() || !loginPassword) return;

    try {
      await login(identifier.trim(), loginPassword);
      navigate(from, { replace: true });
    } catch {
      // Error handled in store
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!username.trim() || !email.trim() || !signupPassword) {
      setValidationError('Please fill in all required fields.');
      return;
    }

    if (username.trim().length < 3) {
      setValidationError('Username must be at least 3 characters long.');
      return;
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(username.trim())) {
      setValidationError('Username can only contain letters, numbers, underscores, and hyphens.');
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setValidationError('Please enter a valid email address.');
      return;
    }

    if (signupPassword.length < 6) {
      setValidationError('Password must be at least 6 characters long.');
      return;
    }

    if (signupPassword !== confirmPassword) {
      setValidationError('Passwords do not match.');
      return;
    }

    try {
      await signup({
        name: name.trim() || undefined,
        username: username.trim(),
        email: email.trim(),
        password: signupPassword,
      });
      navigate(from, { replace: true });
    } catch {
      // Error handled in store
    }
  };

  const displayError = validationError || error;

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="login-badge">
            <ShieldCheck size={14} />
            FinSight AI Secure Access
          </div>
          <h1 className="login-title">
            {mode === 'login' ? 'Sign In' : 'Create Account'}
          </h1>
          <p className="login-subtitle">
            {mode === 'login'
              ? 'Enter your credentials to access institutional analytics and AI explanations.'
              : 'Create a new account to unlock market forecasts and portfolio risk intelligence.'}
          </p>
        </div>

        {/* ── Mode Switcher Tabs ────────────────────────── */}
        <div className="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            className={`auth-tab ${mode === 'login' ? 'auth-tab--active' : ''}`}
            onClick={() => handleTabChange('login')}
          >
            <LogIn size={14} />
            <span>Log In</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'signup'}
            className={`auth-tab ${mode === 'signup' ? 'auth-tab--active' : ''}`}
            onClick={() => handleTabChange('signup')}
          >
            <UserPlus size={14} />
            <span>Sign Up</span>
          </button>
        </div>

        {displayError && (
          <div className="login-error" role="alert">
            <AlertCircle size={16} />
            <span>{displayError}</span>
          </div>
        )}

        {/* ── Sign In Form ──────────────────────────────── */}
        {mode === 'login' ? (
          <form className="login-form" onSubmit={handleLoginSubmit}>
            <div className="login-field">
              <label className="login-label" htmlFor="login-identifier">
                Email or Username
              </label>
              <div className="login-input-wrap">
                <span className="login-input-icon">
                  <Mail size={16} />
                </span>
                <input
                  id="login-identifier"
                  type="text"
                  className="login-input"
                  placeholder="yourname@domain.com or username"
                  value={identifier}
                  onChange={(e) => {
                    setIdentifier(e.target.value);
                    if (displayError) {
                      clearError();
                      setValidationError(null);
                    }
                  }}
                  autoComplete="username"
                  required
                  autoFocus
                />
              </div>
            </div>

            <div className="login-field">
              <label className="login-label" htmlFor="login-password">
                Password
              </label>
              <div className="login-input-wrap">
                <span className="login-input-icon">
                  <Lock size={16} />
                </span>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  className="login-input"
                  placeholder="••••••••••••"
                  value={loginPassword}
                  onChange={(e) => {
                    setLoginPassword(e.target.value);
                    if (displayError) {
                      clearError();
                      setValidationError(null);
                    }
                  }}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="login-password-toggle"
                  onClick={() => setShowPassword((prev) => !prev)}
                  title={showPassword ? 'Hide password' : 'Show password'}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="login-btn"
              disabled={isLoading || !identifier.trim() || !loginPassword}
            >
              {isLoading ? (
                <>
                  <div className="spinner spinner--sm" />
                  <span>Signing In...</span>
                </>
              ) : (
                <span>Log In to Account</span>
              )}
            </button>
          </form>
        ) : (
          /* ── Sign Up Form ──────────────────────────────── */
          <form className="login-form" onSubmit={handleSignupSubmit}>
            <div className="login-field">
              <label className="login-label" htmlFor="signup-name">
                <span>Full Name</span>
                <span className="login-label-hint">Optional</span>
              </label>
              <div className="login-input-wrap">
                <span className="login-input-icon">
                  <User size={16} />
                </span>
                <input
                  id="signup-name"
                  type="text"
                  className="login-input"
                  placeholder="e.g. John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                />
              </div>
            </div>

            <div className="login-field">
              <label className="login-label" htmlFor="signup-username">
                Username
              </label>
              <div className="login-input-wrap">
                <span className="login-input-icon">
                  <User size={16} />
                </span>
                <input
                  id="signup-username"
                  type="text"
                  className="login-input"
                  placeholder="e.g. investor_john"
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    if (displayError) {
                      clearError();
                      setValidationError(null);
                    }
                  }}
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            <div className="login-field">
              <label className="login-label" htmlFor="signup-email">
                Email Address
              </label>
              <div className="login-input-wrap">
                <span className="login-input-icon">
                  <Mail size={16} />
                </span>
                <input
                  id="signup-email"
                  type="email"
                  className="login-input"
                  placeholder="john@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (displayError) {
                      clearError();
                      setValidationError(null);
                    }
                  }}
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            <div className="login-field">
              <label className="login-label" htmlFor="signup-password">
                Password
              </label>
              <div className="login-input-wrap">
                <span className="login-input-icon">
                  <Lock size={16} />
                </span>
                <input
                  id="signup-password"
                  type={showPassword ? 'text' : 'password'}
                  className="login-input"
                  placeholder="At least 6 characters"
                  value={signupPassword}
                  onChange={(e) => {
                    setSignupPassword(e.target.value);
                    if (displayError) {
                      clearError();
                      setValidationError(null);
                    }
                  }}
                  autoComplete="new-password"
                  required
                />
                <button
                  type="button"
                  className="login-password-toggle"
                  onClick={() => setShowPassword((prev) => !prev)}
                  title={showPassword ? 'Hide password' : 'Show password'}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="login-field">
              <label className="login-label" htmlFor="signup-confirm-password">
                Confirm Password
              </label>
              <div className="login-input-wrap">
                <span className="login-input-icon">
                  <Lock size={16} />
                </span>
                <input
                  id="signup-confirm-password"
                  type={showPassword ? 'text' : 'password'}
                  className="login-input"
                  placeholder="Re-enter your password"
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (displayError) {
                      clearError();
                      setValidationError(null);
                    }
                  }}
                  autoComplete="new-password"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="login-btn"
              disabled={isLoading || !username.trim() || !email.trim() || !signupPassword}
            >
              {isLoading ? (
                <>
                  <div className="spinner spinner--sm" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <span>Create FinSight Account</span>
              )}
            </button>
          </form>
        )}

        {/* ── Switcher Bottom Link ──────────────────────── */}
        <div className="auth-switch-footer">
          {mode === 'login' ? (
            <span>
              Don't have an account?{' '}
              <button
                type="button"
                className="auth-switch-btn"
                onClick={() => handleTabChange('signup')}
              >
                Sign Up to create account
              </button>
            </span>
          ) : (
            <span>
              Already have an account?{' '}
              <button
                type="button"
                className="auth-switch-btn"
                onClick={() => handleTabChange('login')}
              >
                Log In to your account
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
