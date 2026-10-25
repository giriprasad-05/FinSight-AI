# FinSight AI - Frontend Documentation

## Overview
FinSight AI is a comprehensive, modern React application designed to provide users with intelligent stock market analytics, AI-driven risk assessments, and an interactive educational investment mentor. It leverages modern frontend architectures to deliver a seamless, responsive, and highly interactive user experience.

---

## 🛠 Tech Stack & Architecture

- **Framework**: [React 19](https://react.dev/) with [TypeScript](https://www.typescriptlang.org/)
- **Build Tool**: [Vite](https://vitejs.dev/) for blazing-fast HMR and optimized production builds.
- **State Management**: [Zustand](https://github.com/pmndrs/zustand) for lightweight, predictable global state (`stockStore`, `mentorStore`, `authStore`).
- **Data Fetching & Caching**: [TanStack React Query](https://tanstack.com/query/latest) for robust asynchronous state management and API caching.
- **Routing**: [React Router DOM](https://reactrouter.com/) for client-side navigation (`/` for Home, `/stock/:ticker` for specific stocks).
- **Styling**: Modular CSS (`global.css`, `primitives.css`) paired with semantic HTML and custom CSS variables for a consistent design system.
- **Data Visualization**: [Recharts](https://recharts.org/) for rendering historical price charts and trend overlays.
- **Animations**: [Framer Motion](https://www.framer.com/motion/) for smooth micro-interactions and transitions.
- **Icons**: [Lucide React](https://lucide.dev/) for consistent vector iconography.

---

## 📂 Project Structure

```text
src/
├── assets/          # Static assets (images, fonts)
├── components/      # Shared, reusable UI components
│   ├── layout/      # Navbar, sidebars, page wrappers
│   └── search/      # Global stock search bar
├── data/            # Mock data, constants, and static content (e.g., AI mentor prompts)
├── features/        # Feature-based modular domains
│   ├── chart/       # Interactive stock price charts (Recharts)
│   ├── education/   # Financial literacy and concept explanations
│   ├── explainability/# Explainable AI components for risk/trend rationale
│   ├── mentor/      # AI Investment Mentor Chatbot UI and logic
│   ├── risk/        # Risk Assessment and AI Trend Analysis modules
│   └── stock/       # Stock overview, metrics, and dashboards
├── hooks/           # Custom React hooks (e.g., useMentor, useStockData)
├── lib/             # Utility functions and external library configurations
├── pages/           # High-level route components (Home, StockDashboard)
├── services/        # API integration layers and network requests
├── store/           # Zustand stores for global state
├── styles/          # Global stylesheets and design tokens
└── types/           # Global TypeScript interfaces and type definitions
```

---

## 🚀 Key Functionalities & Features

### 1. Global Stock Search & Routing
- **Search Component (`components/search`)**: Users can search for stock tickers globally from the Navigation bar.
- **Dynamic Routing**: Selecting a stock routes the user dynamically to `/stock/:ticker`, instantly loading the dashboard for that specific entity using React Router.

### 2. Interactive Price Charts (`features/chart`)
- **Visual Data**: Leverages `Recharts` to render historical price movements.
- **Timeframes**: Users can toggle between various time ranges (e.g., 1D, 1W, 1M, YTD, 1Y, 5Y).
- **Data Handling**: React Query handles fetching and caching the time-series data seamlessly.

### 3. AI Risk & Trend Analysis (`features/risk`)
- **Trend Analysis**: Displays AI-generated stock trajectories (e.g., *Bullish, Bearish, Neutral, Volatile*) based on technical and fundamental drivers.
- **Risk Assessment**: Assigns a risk score to stocks (Low, Medium, High, Very High) accompanied by an algorithmic confidence percentage.
- **Key Drivers**: Visually breaks down the signals driving the AI's conclusion (e.g., *Moving Averages, RSI, Volume Trends*).

### 4. AI Investment Mentor (`features/mentor`)
- **Interactive Chatbot**: An embedded AI assistant designed to educate the user.
- **Context-Aware**: The mentor is aware of the current stock being viewed (`mentorStore`, `useMentor` hook).
- **Educational Explanations**: Capable of breaking down complex financial jargon such as Beta, P/E Ratios, Market Cap, and why a stock was rated *Bullish* or *Bearish*.
- **Quick Prompts**: Contextual suggestion buttons ("What is P/E?", "Explain the risk score") to guide novice investors.

### 5. Explainable AI & Education (`features/explainability`, `features/education`)
- **Transparency**: Instead of simply giving a score, the app provides "explainability" modules that break down *why* an AI made a certain prediction (e.g., Feature Importances, Moving Average crossovers).
- **Educational Overlays**: Disclaimers and tooltips emphasizing that AI outputs are educational pattern observations, not guaranteed financial advice.

### 6. State & Cache Management
- **Zustand (`store/`)**: Used for synchronous UI state that needs to be accessed across disparate components (like toggling the AI Mentor sidebar or storing the user's authentication context).
- **React Query (`App.tsx`)**: Manages all asynchronous API calls, eliminating race conditions, managing loading/error states out-of-the-box, and caching stock data to prevent redundant network requests.

---

## 💻 Getting Started

### Prerequisites
- Node.js (v18+ recommended)
- npm or yarn

### Installation
1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Build for production:
   ```bash
   npm run build
   ```

4. Run the linter:
   ```bash
   npm run lint
   ```

---

## 🎨 Design Philosophy
- **Component-Driven**: Following a feature-sliced design pattern, code is grouped by feature rather than type (e.g., `features/chart` contains everything chart-related) to maintain scalability.
- **Responsive**: Mobile-first CSS ensures the dashboard is accessible and beautiful on all screen sizes.
- **Type-Safe**: Strict TypeScript configuration (`tsconfig.app.json` with `"typeAware": true` in Oxlint) guarantees fewer runtime errors and superior developer experience.
