import { useState } from 'react';
import { ChevronDown, Flame, FileCheck, Users, Wrench, Scale, Brain } from 'lucide-react';

const AGENT_META: Record<string, { label: string; icon: typeof Flame }> = {
  sensor: { label: 'Sensor Agent', icon: Flame },
  permit: { label: 'Permit Agent', icon: FileCheck },
  worker: { label: 'Worker Agent', icon: Users },
  equipment: { label: 'Equipment Agent', icon: Wrench },
  compliance: { label: 'Compliance Agent', icon: Scale },
  planner: { label: 'Planner Agent', icon: Brain },
};

const ORDER = ['sensor', 'permit', 'worker', 'equipment', 'compliance', 'planner'];

export function AgentAccordion({ findings }: { findings: Record<string, string> }) {
  const [open, setOpen] = useState<string | null>('planner');
  const keys = ORDER.filter((k) => findings[k]);

  return (
    <div className="space-y-1">
      {keys.map((key) => {
        const meta = AGENT_META[key] || { label: key, icon: Brain };
        const Icon = meta.icon;
        const isOpen = open === key;
        return (
          <div key={key} className="border border-line rounded-xl overflow-hidden shadow-card">
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : key)}
              className="w-full flex items-center justify-between px-3 py-2 bg-bg-base hover:bg-bg-elevated text-left"
            >
              <span className="flex items-center gap-2 text-xs font-medium">
                <Icon size={14} className="text-accent" />
                {meta.label}
              </span>
              <ChevronDown size={14} className={`text-ink-secondary transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>
            {isOpen && (
              <div className="px-3 py-2 text-xs text-ink-secondary border-t border-line leading-relaxed">
                {findings[key]}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
