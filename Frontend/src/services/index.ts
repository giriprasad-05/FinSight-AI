// ── Service index — the ONE place to swap mock ↔ real ─────────
// To switch to real backend: set VITE_USE_MOCK=false in .env
import { mockStockService } from './stockService';
import { mockMentorService } from './mentorService';

export const stockService = mockStockService;
export const mentorService = mockMentorService;

// Future: conditional swap (when backend is ready)
// const useMock = import.meta.env.VITE_USE_MOCK === 'true';
// export const stockService = useMock ? mockStockService : apiStockService;
// export const mentorService = useMock ? mockMentorService : apiMentorService;
