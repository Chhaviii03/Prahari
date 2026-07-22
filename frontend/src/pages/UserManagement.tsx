import { useEffect, useState } from 'react';
import { Users, Shield } from 'lucide-react';
import { api } from '../api';

type AdminUser = {
  user_id: string;
  username: string;
  name: string;
  role: string;
  zone_id?: string;
};

const ROLE_LABELS: Record<string, string> = {
  safety_officer: 'Safety Officer',
  permit_officer: 'Permit Officer',
  supervisor: 'Supervisor',
  compliance_officer: 'Compliance Officer',
  executive: 'Executive',
  worker: 'Worker',
  admin: 'Administrator',
};

export function UserManagementPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);

  useEffect(() => {
    api.getAdminUsers().then((d) => setUsers(d.users));
  }, []);

  return (
    <div className="p-4 h-full flex flex-col max-w-4xl">
      <header className="mb-4">
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <Users className="text-accent" size={20} /> User Management
        </h1>
        <p className="text-xs text-text-secondary">
          RBAC admin — roles per §5 persona matrix, enforced by policy layer (§17.2, §20)
        </p>
      </header>

      <div className="bg-bg-surface border border-gray-800 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-text-secondary border-b border-gray-800 bg-bg-base">
              <th className="text-left p-3">User</th>
              <th className="text-left p-3">Username</th>
              <th className="text-left p-3">Role</th>
              <th className="text-left p-3">Zone</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id} className="border-b border-gray-800/50 hover:bg-bg-elevated">
                <td className="p-3 font-medium">{u.name}</td>
                <td className="p-3 font-mono text-xs text-accent">{u.username}</td>
                <td className="p-3">
                  <span className="text-xs bg-bg-base border border-gray-700 rounded px-2 py-0.5 flex items-center gap-1 w-fit">
                    <Shield size={10} /> {ROLE_LABELS[u.role] || u.role}
                  </span>
                </td>
                <td className="p-3 text-xs text-text-secondary">{u.zone_id || 'Plant-wide'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[10px] text-text-secondary mt-4">
        Demo accounts use password <code className="text-accent">prahari</code>. Production: SAML/OIDC/Azure AD + OPA policies (§17.4).
      </p>
    </div>
  );
}
