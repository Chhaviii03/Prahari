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
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <Bot className="text-accent" size={20} /> AI Copilot
        </h1>
        <p className="text-xs text-text-secondary">
          Grounded Q&A from Evidence Package, RAG corpus, and Digital Twin — tool-grounded, cited, never free-form (§19.1)
        </p>
      </header>

      {risks.length > 0 && (
        <div className="mb-3 flex items-center gap-2 text-xs">
          <span className="text-text-secondary">Context risk:</span>
          <select
            value={riskId}
            onChange={(e) => setRiskId(e.target.value)}
            className="bg-bg-surface border border-gray-700 rounded px-2 py-1"
          >
            {risks.map((item) => (
              <option key={item.risk.risk_id} value={item.risk.risk_id}>
                {item.risk.zone_id} · {item.risk.motif_id} · CRS {item.risk.crs.score}
              </option>
            ))}
          </select>
          {riskId && (
            <button onClick={() => navigate(`/risk/${riskId}`)} className="text-accent hover:underline">
              Open Evidence →
            </button>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {history.length === 0 && (
          <div className="bg-bg-surface border border-gray-800 rounded-lg p-6 text-center">
            <BookOpen className="mx-auto text-text-secondary mb-2" size={32} />
            <p className="text-sm text-text-secondary">Ask about the current hazard, regulations, or precedent.</p>
            <div className="flex flex-wrap gap-2 justify-center mt-4">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="text-xs bg-bg-base border border-gray-700 rounded-full px-3 py-1 hover:border-accent"
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
            <div className="bg-bg-surface border border-gray-800 rounded-lg p-4 text-sm leading-relaxed">
              {h.r.answer}
              {h.r.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-800">
                  <div className="text-[10px] text-text-secondary uppercase mb-1">Citations</div>
                  {h.r.citations.map((c, j) => (
                    <div key={j} className="text-xs bg-bg-base rounded p-2 mb-1">
                      <span className="text-accent font-mono">{c.framework} {c.ref}</span>
                      <p className="text-text-secondary mt-0.5">{c.text}</p>
                    </div>
                  ))}
                </div>
              )}
              <div className="text-[10px] text-text-secondary mt-2">
                Sources: {h.r.sources.join(' · ')} · grounded={String(h.r.grounded)}
              </div>
            </div>
          </div>
        ))}
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); ask(question); }}
        className="flex gap-2"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Why was C-12 flagged? What does OISD say?"
          className="flex-1 bg-bg-surface border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-accent"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-accent text-white px-4 py-2 rounded text-sm flex items-center gap-1 disabled:opacity-50"
        >
          <Send size={14} /> {loading ? '...' : 'Ask'}
        </button>
      </form>
    </div>
  );
}
