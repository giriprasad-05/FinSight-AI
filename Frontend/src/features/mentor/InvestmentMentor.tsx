import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useMentor } from '@/hooks/useMentor';
import { Send, MessageSquare, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export function InvestmentMentor(): React.ReactElement {
  const { ticker: urlTicker } = useParams<{ ticker: string }>();
  const currentTicker = urlTicker?.toUpperCase() || '';

  const { messages, isLoading, sendMessage } = useMentor(currentTicker);
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

  const handleChipClick = (prompt: string) => {
    if (isLoading) return;
    sendMessage(prompt);
  };

  const suggestedPrompts = [
    'Why is this stock risky?',
    'Explain the RSI for this stock.',
    'Why does the model predict this trend?',
    'What are the top factors affecting this stock?',
    "Explain this stock like I'm a beginner.",
  ];

  return (
    <div className="card mentor-card">
      <div className="mentor-header">
        <MessageSquare size={16} />
        Ask FinSight AI about {currentTicker || 'Stock'}
      </div>
      <div className="mentor-subtitle">
        Questions answered specifically about {currentTicker || 'the current stock'} using FinSight's real analysis.
      </div>

      <div className="mentor-chat">
        <div className="mentor-messages" ref={scrollRef}>
          {messages.map((m) => (
            <div key={m.id} className={`chat-bubble-wrap chat-bubble-wrap--${m.role}`}>
              {m.role === 'assistant' && <div className="chat-avatar">AI</div>}
              <div className={`chat-bubble chat-bubble--${m.role}`}>
                {m.role === 'assistant' ? (
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                ) : (
                  m.content
                )}
              </div>
              {m.role === 'user' && (
                <div
                  className="chat-avatar"
                  style={{
                    background: 'var(--color-bg-base)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  U
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="chat-bubble-wrap chat-bubble-wrap--assistant">
              <div className="chat-avatar">AI</div>
              <div className="chat-bubble chat-bubble--assistant">
                <span className="mentor-loading-text">
                  <Sparkles size={14} style={{ animation: 'spin 2s linear infinite' }} />
                  Analyzing {currentTicker || 'stock'}...
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Quick prompt suggestions */}
        <div className="mentor-chips">
          {suggestedPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="mentor-chip-btn"
              disabled={isLoading}
              onClick={() => handleChipClick(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>

        <form className="mentor-input-wrap" onSubmit={handleSubmit}>
          <textarea
            className="mentor-input"
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask FinSight AI about ${currentTicker || 'this stock'}...`}
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
