import { create } from 'zustand';
import type { ChatMessage, MentorContext } from '@/types';
import { format } from 'date-fns';

interface MentorState {
  messages: ChatMessage[];
  isLoading: boolean;
  isOpen: boolean;
  context: MentorContext | null;

  // ── Actions ─────────────────────────────────────────────────
  setContext: (ctx: MentorContext) => void;
  addMessage: (msg: ChatMessage) => void;
  setLoading: (val: boolean) => void;
  clearConversation: () => void;
  openMentor: () => void;
  closeMentor: () => void;
  toggleMentor: () => void;
}

function makeWelcomeMessage(ctx: MentorContext): ChatMessage {
  return {
    id: `welcome-${ctx.ticker}`,
    role: 'assistant',
    content: `👋 Hello! I'm your **AI Investment Mentor** for **${ctx.ticker} — ${ctx.companyName}**.\n\nI can help you understand:\n• What the **${ctx.riskLevel} risk rating** means for this stock\n• The current **${ctx.trendDirection} trend** analysis\n• Financial concepts like P/E ratio, beta, volatility, and more\n\nI'm an educational tool — I won't tell you what to buy or sell. But I'll help you make sense of what you're seeing.\n\n_Try asking: "What is beta?" or "What does the risk score mean?"_`,
    timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
  };
}

export const useMentorStore = create<MentorState>((set) => ({
  messages: [],
  isLoading: false,
  isOpen: false,
  context: null,

  setContext: (ctx) =>
    set({
      context: ctx,
      messages: [makeWelcomeMessage(ctx)],
    }),

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  setLoading: (val) => set({ isLoading: val }),

  clearConversation: () =>
    set((state) => ({
      messages: state.context ? [makeWelcomeMessage(state.context)] : [],
    })),

  openMentor: () => set({ isOpen: true }),
  closeMentor: () => set({ isOpen: false }),
  toggleMentor: () => set((state) => ({ isOpen: !state.isOpen })),
}));
