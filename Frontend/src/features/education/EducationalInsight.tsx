import React from 'react';
import type { EducationalInsight as EducationalInsightType } from '@/types';
import { BookOpen } from 'lucide-react';

interface EducationalInsightProps {
  insight: EducationalInsightType;
}

export function EducationalInsight({ insight }: EducationalInsightProps): React.ReactElement {
  return (
    <div className="card learn-card">
      <div className="learn-header">
        <BookOpen size={16} />
        Learn
      </div>
      <div className="learn-title">
        {insight.title}
      </div>
      <div className="learn-body">
        {insight.body}
      </div>
    </div>
  );
}
