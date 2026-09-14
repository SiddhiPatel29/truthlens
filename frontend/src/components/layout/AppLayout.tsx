import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { useAuth } from '../../context/AuthContext';
import { Bell, LogOut, User } from 'lucide-react';

export const AppLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="container-full">
      <Sidebar />
      <div className="main-content">
        {/* Top Header */}
        <header
          style={{
            height: '64px',
            borderBottom: '1px solid var(--border-color)',
            backgroundColor: 'rgba(11, 15, 25, 0.8)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 2rem',
            position: 'sticky',
            top: 0,
            zIndex: 40,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Platform /</span>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#ffffff' }}>Operational Console</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            {/* Notification bell */}
            <button
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '6px',
                borderRadius: '6px',
              }}
              title="System Alerts"
            >
              <Bell size={18} />
            </button>

            <div style={{ height: '24px', width: '1px', backgroundColor: 'var(--border-color)' }} />

            {/* User Profile display */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--accent-blue)',
                }}
              >
                <User size={18} />
              </div>
              <div>
                <div style={{ fontSize: '0.825rem', fontWeight: 600, color: '#f8fafc' }}>
                  {user?.name || 'Administrator'}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {user?.email || 'admin@veramedia.ai'}
                </div>
              </div>
            </div>

            {/* Logout button */}
            <button
              onClick={handleLogout}
              style={{
                background: 'transparent',
                border: '1px solid var(--border-color)',
                color: 'var(--text-secondary)',
                padding: '6px 10px',
                borderRadius: '6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                fontSize: '0.75rem',
                fontWeight: 500,
              }}
              title="Sign Out"
            >
              <LogOut size={14} />
              <span>Logout</span>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main style={{ flex: 1 }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
};
