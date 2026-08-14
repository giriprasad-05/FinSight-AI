import React, { useState } from 'react';
import { Lightbulb, ChevronDown } from 'lucide-react';
import type { FeatureImportance } from '@/types';

interface ExplainableAIProps {
  summary: string;
  features: FeatureImportance[];
}

export function ExplainableAI({ summary }: ExplainableAIProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="card explain-card">
      <button className="explain-toggle" onClick={() => setIsOpen(!isOpen)}>
        <div className="explain-title-wrap">
          <Lightbulb size={16} />
          Why did the model produce this result?
        </div>
        <ChevronDown size={16} className={`explain-chevron ${isOpen ? 'explain-chevron--open' : ''}`} />
      </button>

      {isOpen && (
        <div className="explain-content">
          <div className="explain-text">
            {summary}
          </div>
        </div>
      )}
    </div>
  );
}
