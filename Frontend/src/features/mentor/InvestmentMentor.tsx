import React, { useState, useEffect, useRef } from 'react';
import { useMentor } from '@/hooks/useMentor';
import { Send, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export function InvestmentMentor(): React.ReactElement {
  const { messages, isLoading, sendMessage } = useMentor();
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="card mentor-card">
      <div className="mentor-header">
        <MessageSquare size={16} />
        AI Investment Mentor
      </div>
      <div className="mentor-subtitle">
        Ask questions about the selected stock or financial concepts.
      </div>
      
      <div className="mentor-chat">
        <div className="mentor-messages" ref={scrollRef}>
          {messages.map(m => (
            <div key={m.id} className={`chat-bubble-wrap chat-bubble-wrap--${m.role}`}>
              {m.role === 'assistant' && <div className="chat-avatar">AI</div>}
              <div className={`chat-bubble chat-bubble--${m.role}`}>
                {m.role === 'assistant' ? (
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                ) : (
                  m.content
                )}
              </div>
              {m.role === 'user' && <div className="chat-avatar" style={{ background: 'var(--color-bg-base)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>U</div>}
            </div>
          ))}
          {isLoading && (
            <div className="chat-bubble-wrap chat-bubble-wrap--assistant">
              <div className="chat-avatar">AI</div>
              <div className="chat-bubble chat-bubble--assistant">...</div>
            </div>
          )}
        </div>



        <form className="mentor-input-wrap" onSubmit={handleSubmit}>
          <textarea
            className="mentor-input"
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your question..."
          />
          <button
            type="submit"
            className="mentor-send"
            disabled={!input.trim() || isLoading}
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
