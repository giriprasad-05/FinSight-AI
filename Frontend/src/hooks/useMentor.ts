import { useCallback } from 'react';
import { useMentorStore } from '@/store/mentorStore';
import { mentorService } from '@/services';
import type { ChatMessage, MentorContext } from '@/types';
import { format } from 'date-fns';

export function useMentor(fallbackTicker?: string) {
  const store = useMentorStore();

  const sendMessage = useCallback(
    async (text: string) => {
      const activeTicker = store.context?.ticker || fallbackTicker;
      if (!activeTicker || !text.trim()) return;

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: text.trim(),
        timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
      };

      // Snapshot prior messages for conversation memory
      const conversationSnapshot = store.messages;

      store.addMessage(userMsg);
      store.setLoading(true);

      const ctx: MentorContext = store.context || {
        ticker: activeTicker,
        companyName: activeTicker,
        riskLevel: 'Assessing',
        riskScore: 0,
        trendDirection: 'Assessing',
        price: 0,
        priceChangePct: 0,
      };

      try {
        const response = await mentorService.sendMessage(text, ctx, conversationSnapshot);
        store.addMessage(response);
      } catch (err: any) {
        const isUnavailable =
          err?.message?.includes('unavailable') ||
          err?.message?.includes('Failed to fetch') ||
          err?.message?.includes('ECONNREFUSED');

        store.addMessage({
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: isUnavailable
            ? 'Local AI is unavailable.'
            : (err?.message || 'Local AI is unavailable.'),
          timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
        });
      } finally {
        store.setLoading(false);
      }
    },
    [store, fallbackTicker]
  );

  return {
    messages: store.messages,
    isLoading: store.isLoading,
    isOpen: store.isOpen,
    context: store.context,
    sendMessage,
    clearConversation: store.clearConversation,
    openMentor: store.openMentor,
    closeMentor: store.closeMentor,
    toggleMentor: store.toggleMentor,
    setContext: store.setContext,
  };
}
