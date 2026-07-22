import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen, Download, FileText, Shield } from 'lucide-react';
import { api } from '../api';

type Report = {
  report_id: string;
  type: string;
  title: string;
  zone_id?: string;
  risk_id?: string;
  status: string;
  created_at: string;
  exportable: boolean;
};

export function ReportsLibraryPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [exporting, setExporting] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.getReports().then((d) => setReports(d.reports));
  }, []);

  const exportPack = async (r: Report) => {
    if (!r.risk_id) return;
    setExporting(r.report_id);
    try {
      const pack = await api.exportReport(r.risk_id);
      const blob = new Blob([JSON.stringify(pack, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-pack-${r.risk_id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(null);
    }
  };

  const typeIcon = (type: string) => {
    if (type === 'INCIDENT_DRAFT') return FileText;
    if (type === 'AUDIT_ENTRY') return Shield;
    return FolderOpen;
  };

  return (
    <div className="p-4 h-full flex flex-col">
      <header className="mb-4">
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <FolderOpen className="text-accent" size={20} /> Reports Library
        </h1>
        <p className="text-xs text-ink-secondary">
          Audit packs, incident reports, evidence exports — chain-of-custody grade (§21.3)
        </p>
      </header>

      <div className="flex-1 overflow-y-auto space-y-2">
        {reports.length === 0 && (
          <p className="text-sm text-ink-secondary text-center py-8">
            No reports yet. Load a demo scenario to generate evidence packs.
          </p>
        )}
        {reports.map((r) => {
          const Icon = typeIcon(r.type);
          return (
            <div key={r.report_id} className="bg-bg-surface border border-line rounded-xl shadow-card p-4 flex items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <Icon size={18} className="text-accent mt-0.5" />
                <div>
                  <div className="text-sm font-medium">{r.title}</div>
                  <div className="text-xs text-ink-secondary mt-0.5">
                    {r.type} · {r.status} · {new Date(r.created_at).toLocaleString()}
                  </div>
                  {r.zone_id && <div className="text-[10px] text-ink-secondary">Zone {r.zone_id}</div>}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                {r.risk_id && (
                  <button
                    onClick={() => navigate(`/risk/${r.risk_id}`)}
                    className="text-xs border border-line px-3 py-1.5 rounded hover:border-accent"
                  >
                    View
                  </button>
                )}
                {r.exportable && r.risk_id && (
                  <button
                    onClick={() => exportPack(r)}
                    disabled={exporting === r.report_id}
                    className="text-xs bg-accent-peach text-ink-primary px-3 py-1.5 rounded flex items-center gap-1 disabled:opacity-50"
                  >
                    <Download size={12} /> {exporting === r.report_id ? '...' : 'Export Audit Pack'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
