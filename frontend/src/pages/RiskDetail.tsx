import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Shield, AlertOctagon, CheckCircle, MessageSquare, Siren } from 'lucide-react';
import { api } from '../api';
import type { RiskInstance, EvidencePackage } from '../types';
import { SeverityBadge, formatLeadTime } from '../components/ui';
import { AgentAccordion } from '../components/AgentAccordion';

export function RiskDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [risk, setRisk] = useState<RiskInstance | null>(null);
  const [evidence, setEvidence] = useState<EvidencePackage | null>(null);
  const [acting, setActing] = useState(false);
  const [ackNotice, setAckNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.getRisk(id).then(setRisk).catch(console.error);
    api.getEvidence(id).then(setEvidence).catch(() => {});
  }, [id]);

  const handleAck = async () => {
    if (!id) return;
    setActing(true);
    setAckNotice(null);
    try {
      await api.acknowledgeRisk(id, 'Action taken per recommendation');
      setRisk(await api.getRisk(id));
      setAckNotice('Acknowledgement sent to supervisors and compliance officers.');
    } finally {
      setActing(false);
    }
  };

  const handleEmergency = async () => {
    if (!risk) return;
    if (!confirm(`Declare emergency for zone ${risk.zone_id}? (1-step confirm per §21.2)`)) return;
    await api.declareEmergency(risk.zone_id, risk.risk_id);
    navigate('/incident');
  };

  if (!risk) return <div className="p-4 text-text-secondary">Loading risk instance...</div>;

  return (
    <div className="p-4 h-full flex flex-col">
      <button onClick={() => navigate('/')} className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary mb-3">
        <ArrowLeft size={14} /> Back to Dashboard
      </button>

      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <SeverityBadge band={risk.crs.band} score={risk.crs.score} />
            <span className="text-sm font-medium">{risk.zone_id}</span>
            <span className="text-xs text-text-secondary">{risk.motif_id} {risk.motif_version}</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <span>Lead time: {formatLeadTime(risk.lead_time_seconds)}</span>
            <span>·</span>
            <span className="text-sev-ok">detection.llm_involved = {String(risk.detection.llm_involved)}</span>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <Link to={`/copilot?risk=${risk.risk_id}`} className="flex items-center gap-1 bg-bg-elevated border border-gray-700 text-xs px-3 py-1.5 rounded hover:border-accent">
            <MessageSquare size={14} /> AI Copilot
          </Link>
          <button onClick={handleAck} disabled={acting} className="flex items-center gap-1 bg-sev-ok/20 text-sev-ok border border-sev-ok/40 text-xs px-3 py-1.5 rounded">
            <CheckCircle size={14} /> Acknowledge & Act
          </button>
          <button onClick={handleEmergency} className="flex items-center gap-1 bg-sev-critical/20 text-sev-critical border border-sev-critical/40 text-xs px-3 py-1.5 rounded">
            <Siren size={14} /> Declare Emergency
          </button>
        </div>
      </div>

      {ackNotice && (
        <div className="mb-3 text-xs bg-sev-ok/10 border border-sev-ok/40 text-sev-ok rounded p-3 flex items-center gap-2">
          <CheckCircle size={14} /> {ackNotice}
        </div>
      )}

      <div className="flex-1 grid grid-cols-12 gap-4 min-h-0 overflow-hidden">
        <div className="col-span-7 space-y-4 overflow-y-auto">
          {risk.narrative && (
            <div className="bg-bg-surface rounded-lg border border-gray-800 p-4">
              <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Situational Narrative (P4 Planner)</h3>
              <p className="text-sm leading-relaxed">{risk.narrative}</p>
            </div>
          )}

          <div className="bg-bg-surface rounded-lg border border-gray-800 p-4">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Contributing Signals</h3>
            <div className="space-y-2">
              {risk.contributing_signals.map((s, i) => (
                <div key={i} className="flex items-center gap-2 text-sm bg-bg-base rounded p-2">
                  <span className="text-xs font-mono text-accent">{s.type}</span>
                  <span>{s.value}</span>
                </div>
              ))}
            </div>
          </div>

          {evidence && (
            <div className="bg-bg-surface rounded-lg border border-gray-800 p-4">
              <h3 className="text-xs font-medium text-text-secondary uppercase mb-2 flex items-center gap-1">
                <Shield size={14} /> Evidence Package (P5)
              </h3>
              <div className="space-y-3">
                <div>
                  <div className="text-xs text-text-secondary mb-1">Root Cause Hypotheses</div>
                  {evidence.root_cause_hypotheses.map((h) => (
                    <div key={h.rank} className="bg-bg-base rounded p-2 mb-1 text-sm">
                      <span className="text-accent font-mono text-xs">#{h.rank}</span> {h.hypothesis}
                      <span className="text-xs text-text-secondary ml-2">({(h.confidence * 100).toFixed(0)}%)</span>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="text-xs text-text-secondary mb-1">Recommendations (Counterfactual-scored)</div>
                  {evidence.recommendations.map((r, i) => (
                    <div key={i} className="bg-bg-base rounded p-2 mb-1 text-sm border-l-2 border-accent">
                      <div>{r.action}</div>
                      <div className="text-xs text-sev-ok mt-1 tabular-nums">
                        CRS {risk.crs.score.toFixed(0)} → {r.projected_crs_after.toFixed(0)} (counterfactual verified)
                      </div>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="text-xs text-text-secondary mb-1">Regulatory Citations</div>
                  {evidence.regulatory_citations.map((c) => (
                    <div key={c.ref} className="text-sm bg-bg-base rounded p-2 mb-1">
                      <span className="text-accent font-mono text-xs">{c.framework} {c.ref}</span>
                      <p className="text-xs text-text-secondary mt-0.5">{c.text}</p>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="text-xs text-text-secondary mb-1">Historical Precedent</div>
                  {evidence.historical_references.map((h) => (
                    <div key={h.incident_id} className="text-sm bg-bg-base rounded p-2 mb-1">
                      <span className="text-accent font-mono text-xs">{h.incident_id}</span>
                      <span className="text-xs text-text-secondary ml-2">sim {(h.similarity * 100).toFixed(0)}%</span>
                      <p className="text-xs text-text-secondary mt-0.5">{h.summary}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="col-span-5 space-y-4 overflow-y-auto">
          {evidence && (
            <div className="bg-bg-surface rounded-lg border border-gray-800 p-4">
              <h3 className="text-xs font-medium text-text-secondary uppercase mb-3">Multi-Agent Analysis</h3>
              <AgentAccordion findings={evidence.agent_findings} />
            </div>
          )}

          <div className="bg-bg-surface rounded-lg border border-gray-800 p-4">
            <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">Timeline</h3>
            {risk.timeline.map((t, i) => (
              <div key={i} className="flex gap-2 text-xs mb-2">
                <span className="text-text-secondary font-mono whitespace-nowrap">{new Date(t.ts).toLocaleTimeString()}</span>
                <span className="text-accent">{t.event}</span>
                <span className="text-text-secondary">{t.actor}</span>
              </div>
            ))}
          </div>

          <Link to="/heatmap" className="block bg-bg-surface rounded-lg border border-gray-800 p-3 text-xs text-center hover:border-accent">
            View zone on Geospatial Heatmap →
          </Link>
        </div>
      </div>
    </div>
  );
}
