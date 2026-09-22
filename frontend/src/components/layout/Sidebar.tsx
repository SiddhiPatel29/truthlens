import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Shield,
  LayoutDashboard,
  ScanLine,
  SearchCheck,
  History,
  FolderArchive,
  FileCheck2,
  AlertTriangle,
  Settings,
  Activity,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navLinks = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/analyze', label: 'Analyze', icon: ScanLine },
    { to: '/investigations', label: 'Investigations', icon: SearchCheck },
    { to: '/history', label: 'Detection History', icon: History },
    { to: '/vault', label: 'Evidence Vault', icon: FolderArchive },
    { to: '/reports', label: 'Reports', icon: FileCheck2 },
    { to: '/abuse', label: 'Abuse Dispatcher', icon: AlertTriangle },
    { to: '/settings', label: 'Settings', icon: Settings },
    { to: '/health', label: 'System Health', icon: Activity },
  ];

  return (
    <aside
      style={{
        width: '260px',
        backgroundColor: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        height: '100vh',
        position: 'sticky',
        top: 0,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '1.5rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          borderBottom: '1px solid var(--border-color)',
        }}
      >
        <div
          style={{
            background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
            padding: '8px',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(59, 130, 246, 0.4)',
          }}
        >
          <Shield size={22} color="#ffffff" />
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: '1.125rem', letterSpacing: '-0.025em', color: '#ffffff' }}>
            VeraMedia AI
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 500 }}>
            TruthLens Forensics
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav
        style={{
          padding: '1rem 0.75rem',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '0.25rem',
          overflowY: 'auto',
        }}
      >
        {navLinks.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.625rem 0.85rem',
                borderRadius: '8px',
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--bg-surface)' : 'transparent',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.85rem',
                textDecoration: 'none',
                borderLeft: isActive ? '3px solid var(--accent-blue)' : '3px solid transparent',
                transition: 'all 0.15s ease',
              })}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Status Chip */}
      <div
        style={{
          padding: '1rem 1.25rem',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#0a0e1a',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div className="pulse-green" />
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#e2e8f0' }}>System Status: Online</span>
        </div>
        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>v1.0.0</span>
      </div>
    </aside>
  );
};
