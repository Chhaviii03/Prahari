import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Bot, BookOpen } from 'lucide-react';
import { api } from '../api';
import type { DashboardItem } from '../types';

type CopilotResponse = {
  question: string;
  answer: string;
  citations: { framework: string; ref: string; text: string }[];
  sources: string[];
  grounded: boolean;
};

const SUGGESTIONS = [
  'Why was C-12 flagged?',
  'What does OISD say about hot work near confined spaces?',
  'Has this happened before?',
  'What should we do right now?',
  'How many workers are exposed?',
];

export function CopilotPage() {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<{ q: string; r: CopilotResponse }[]>([]);
  const [loading, setLoading] = useState(false);
  const [risks, setRisks] = useState<DashboardItem[]>([]);
  const [riskId, setRiskId] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    api.getDashboard().then((d) => {
      setRisks(d.items);
      if (d.items[0]) setRiskId(d.items[0].risk.risk_id);
    });
  }, []);

  const ask = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    try {
      const r = await api.copilot(q, riskId || undefined);
      setHistory((h) => [...h, { q, r }]);
      setQuestion('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 h-full flex flex-col max-w-4xl mx-auto">
      <header className="mb-4">
        <h1 className="text-lg font-semibold flex items-center gap-2 text-ink-primary">
          <Bot className="text-accent" size={20} /> AI Copilot
        </h1>
        <p className="text-xs text-ink-secondary">
          Grounded Q&A from Evidence Package, RAG corpus, and Digital Twin — tool-grounded, cited, never free-form (§19.1)
        </p>
      </header>

      {risks.length > 0 && (
        <div className="mb-3 flex items-center gap-2 text-xs">
          <span className="text-ink-secondary">Context risk:</span>
          <select
            value={riskId}
            onChange={(e) => setRiskId(e.target.value)}
            className="bg-bg-surface border border-line rounded-xl shadow-card px-2 py-1.5 text-ink-primary"
          >
            {risks.map((item) => (
              <option key={item.risk.risk_id} value={item.risk.risk_id}>
                {item.risk.zone_id} · {item.risk.motif_id} · CRS {item.risk.crs.score}
              </option>
            ))}
          </select>
          {riskId && (
            <button onClick={() => navigate(`/risk/${riskId}`)} className="text-accent hover:underline font-medium">
              Open Evidence →
            </button>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {history.length === 0 && (
          <div className="bg-bg-surface border border-line rounded-2xl p-8 text-center shadow-card">
            <BookOpen className="mx-auto text-accent mb-3" size={32} />
            <p className="text-base font-medium text-ink-primary mb-1">What should we look at first?</p>
            <p className="text-sm text-ink-secondary">Ask about the current hazard, regulations, or precedent.</p>
            <div className="flex flex-wrap gap-2 justify-center mt-5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="text-xs bg-bg-surface border border-line rounded-full px-3 py-1.5 text-ink-secondary hover:border-accent hover:bg-accent-soft hover:text-ink-primary transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {history.map((h, i) => (
          <div key={i} className="space-y-2">
            <div className="text-sm font-medium text-right text-accent">{h.q}</div>
            <div className="bg-bg-surface border border-line rounded-2xl p-4 text-sm leading-relaxed shadow-card text-ink-primary">
              {h.r.answer}
              {h.r.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-line">
                  <div className="text-[10px] text-ink-secondary uppercase mb-1">Citations</div>
                  {h.r.citations.map((c, j) => (
                    <div key={j} className="text-xs bg-accent-soft rounded-xl p-2.5 mb-1">
                      <span className="text-accent font-mono font-medium">{c.framework} {c.ref}</span>
                      <p className="text-ink-secondary mt-0.5">{c.text}</p>
                    </div>
                  ))}
                </div>
              )}
              <div className="text-[10px] text-ink-secondary mt-2">
                Sources: {h.r.sources.join(' · ')} · grounded={String(h.r.grounded)}
              </div>
            </div>
          </div>
        ))}
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); ask(question); }}
        className="flex items-center gap-2 bg-bg-surface border border-line rounded-2xl p-2 shadow-card"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask Prahari about your safety analytics..."
          className="flex-1 bg-transparent border-0 rounded-xl px-3 py-2.5 text-sm text-ink-primary placeholder:text-ink-secondary focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-accent-peach hover:bg-accent-muted text-ink-primary w-10 h-10 rounded-xl flex items-center justify-center disabled:opacity-50 transition-colors shrink-0"
          aria-label="Send"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
