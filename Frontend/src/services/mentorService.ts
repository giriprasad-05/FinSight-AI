import type { ChatMessage, MentorContext } from '@/types';
import { format } from 'date-fns';

// ── Mentor service interface ───────────────────────────────────
export interface MentorService {
  sendMessage(
    text: string,
    context: MentorContext,
    conversation?: ChatMessage[]
  ): Promise<ChatMessage>;
}

// ── Real API implementation connecting to Node -> FastAPI -> LM Studio ─────────
export const apiMentorService: MentorService = {
  async sendMessage(
    text: string,
    context: MentorContext,
    conversation?: ChatMessage[]
  ): Promise<ChatMessage> {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '';

    // Strip greeting/welcome messages from token payload
    const conversationPayload = (conversation || [])
      .filter((m) => !m.id.startsWith('welcome-'))
      .map((m) => ({
        role: m.role,
        content: m.content,
      }));

    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('finsight_token') : null;
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${baseUrl}/api/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ticker: context.ticker,
          message: text,
          conversation: conversationPayload,
        }),
      });

      if (!res.ok) {
        if (res.status === 503) {
          throw new Error('Local AI is unavailable.');
        }
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.error || 'Local AI is unavailable.');
      }

      const data = await res.json();
      return {
        id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role: 'assistant',
        content: data.reply || 'No response received from local AI.',
        timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
      };
    } catch (err: any) {
      if (err.message && err.message.includes('Failed to fetch')) {
        throw new Error('Local AI is unavailable.');
      }
      throw err;
    }
  },
};
