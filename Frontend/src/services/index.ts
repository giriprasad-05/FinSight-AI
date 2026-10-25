// ── Service index — the ONE place to swap mock ↔ real ─────────
// To switch to the real Node.js backend, set in Frontend/.env:
//   VITE_USE_MOCK=false
//   VITE_API_BASE_URL=http://localhost:5000
import { mockStockService } from './stockService';
import { apiStockService } from './apiService';
import { apiMentorService } from './mentorService';

const useMock = import.meta.env.VITE_USE_MOCK !== 'false';

export const stockService = useMock ? mockStockService : apiStockService;
export const mentorService = apiMentorService;
export { authService } from './authService';
