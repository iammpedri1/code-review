export interface ReviewFinding {
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  line: number;
  evidence: string;
  description: string;
  suggestion: string;
  category: string;
}

export interface ReviewResponse {
  summary: string;
  findings: ReviewFinding[];
  provider: 'local' | 'openrouter' | 'gemini';
}

export interface ReviewRequest {
  code: string;
  language: string;
  useAi: boolean;
  provider: 'openrouter' | 'gemini';
}
