import type { ChatMessage, MentorContext } from '@/types';
import { findMentorResponse } from '@/data/stocks/chatbot';
import { format } from 'date-fns';

// ── Mentor service interface ───────────────────────────────────
export interface MentorService {
  sendMessage(text: string, context: MentorContext): Promise<ChatMessage>;
}

// ── Simulate streaming response delay ─────────────────────────
function streamDelay(): Promise<void> {
  const ms = 600 + Math.random() * 1200; // 600–1800ms realistic
  return new Promise(resolve => setTimeout(resolve, ms));
}

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ── Mock implementation ───────────────────────────────────────
export const mockMentorService: MentorService = {
  async sendMessage(text: string, context: MentorContext): Promise<ChatMessage> {
    await streamDelay();
    const content = findMentorResponse(text, context);
    return {
      id: generateId(),
      role: 'assistant',
      content,
      timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
    };
  },
};
