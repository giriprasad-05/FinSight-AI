import React from 'react';
import { NavLink } from 'react-router-dom';
import { User } from 'lucide-react';
export { StockSearch } from '@/components/search/StockSearch';

export function Navbar(): React.ReactElement {
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
        <a href="#learn" className="navbar__nav-link">
          Learn
        </a>
        <a href="#about" className="navbar__nav-link">
          About
        </a>
      </div>

      <div className="navbar__right">
        <button
          type="button"
          className="navbar__avatar"
          title="User Profile"
          aria-label="User Profile"
        >
          <User size={16} />
        </button>
      </div>
    </nav>
  );
}
