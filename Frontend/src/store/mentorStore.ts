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
  const riskInfo = ctx.riskScore > 0 ? `Score: ${ctx.riskScore} (${ctx.riskLevel} Risk)` : `${ctx.riskLevel} Risk`;
  return {
    id: `welcome-${ctx.ticker}`,
    role: 'assistant',
    content: `👋 Hello! I'm FinSight AI, your dedicated analysis assistant for **${ctx.ticker}**.\n\nI answer questions specifically about **${ctx.ticker}** using FinSight's real quantitative analysis:\n• **Risk Profile**: ${riskInfo}\n• **Model Trend**: ${ctx.trendDirection}\n• Technical indicators (RSI, MACD, Moving Averages)\n• Top model drivers & watch items\n\n_Ask a question below or choose a suggestion to get started!_`,
    timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
  };
}

export const useMentorStore = create<MentorState>((set) => ({
  messages: [],
  isLoading: false,
  isOpen: false,
  context: null,

  setContext: (ctx) =>
    set((state) => {
      if (state.context?.ticker === ctx.ticker) {
        return { context: ctx };
      }
      return {
        context: ctx,
        messages: [makeWelcomeMessage(ctx)],
      };
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
