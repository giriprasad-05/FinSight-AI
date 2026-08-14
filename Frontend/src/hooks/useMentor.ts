import { useCallback } from 'react';
import { useMentorStore } from '@/store/mentorStore';
import { mentorService } from '@/services';
import type { ChatMessage } from '@/types';
import { format } from 'date-fns';

export function useMentor() {
  const store = useMentorStore();

  const sendMessage = useCallback(
    async (text: string) => {
      if (!store.context || !text.trim()) return;

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: text.trim(),
        timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
      };

      store.addMessage(userMsg);
      store.setLoading(true);

      try {
        const response = await mentorService.sendMessage(text, store.context);
        store.addMessage(response);
      } catch {
        store.addMessage({
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: 'I encountered a technical issue. Please try again in a moment.',
          timestamp: format(new Date(), "yyyy-MM-dd'T'HH:mm:ss"),
        });
      } finally {
        store.setLoading(false);
      }
    },
    [store]
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
