import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { User, LogOut, LogIn } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

export { StockSearch } from '@/components/search/StockSearch';

export function Navbar(): React.ReactElement {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <nav className="navbar">
      <div className="navbar__left">
        <NavLink to="/" className="navbar__logo">
          FinSight AI
        </NavLink>
      </div>

      <div className="navbar__nav">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `navbar__nav-link${isActive ? ' navbar__nav-link--active' : ''}`
          }
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/about"
          className={({ isActive }) =>
            `navbar__nav-link${isActive ? ' navbar__nav-link--active' : ''}`
          }
        >
          About
        </NavLink>
      </div>

      <div className="navbar__right">
        {isAuthenticated ? (
          <div className="navbar__user-info">
            <div className="navbar__user-pill" title={user?.email || user?.name || 'Logged in'}>
              <User size={13} />
              <span className="navbar__user-name">{user?.username || 'demo'}</span>
            </div>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={handleLogout}
              title="Log Out"
              aria-label="Log Out"
            >
              <LogOut size={13} />
              <span>Log Out</span>
            </button>
          </div>
        ) : (
          <NavLink
            to="/login"
            className="btn btn--primary btn--sm"
            title="Sign In"
            aria-label="Sign In"
          >
            <LogIn size={13} />
            <span>Sign In</span>
          </NavLink>
        )}
      </div>
    </nav>
  );
}
