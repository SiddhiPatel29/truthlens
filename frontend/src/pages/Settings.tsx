import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  User,
  Shield,
  Key,
  Bell,
  Sliders,
  LogOut,
  Eye,
  EyeOff,
  Lock,
  Laptop,
  Globe,
  Volume2,
  Check,
  Copy,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  Send,
  Zap,
} from 'lucide-react';

export const Settings: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'Profile' | 'Security' | 'Notifications' | 'Preferences'>('Profile');

  // Load saved settings or use defaults
  const savedSettings = (() => {
    try {
      const raw = localStorage.getItem('analyst_settings');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  })();

  // Profile States - connected to authenticated user from /api/auth/me
  const [name, setName] = useState(savedSettings?.name || user?.name || 'Forensic Analyst');
  const [email, setEmail] = useState(savedSettings?.email || user?.email || 'analyst@truthlens.local');
  const [agency, setAgency] = useState(savedSettings?.agency || 'Digital Forensics Unit');
  const [bio, setBio] = useState(savedSettings?.bio || 'Forensic examiner specializing in media verification, statistical signal analysis, and forensic artifact inspection.');

  useEffect(() => {
    if (user?.name && !savedSettings?.name) {
      setName(user.name);
    }
    if (user?.email && !savedSettings?.email) {
      setEmail(user.email);
    }
  }, [user]);

  // Security States
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [apiKey, setApiKey] = useState(savedSettings?.apiKey || 'vm_live_8f3b4c129e4a8b7c6d5e1f2a3b4c');
  const [twoFactor, setTwoFactor] = useState(savedSettings?.twoFactor ?? false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  // Notifications States
  const [emailAlerts, setEmailAlerts] = useState(savedSettings?.emailAlerts ?? false);
  const [webhookAlerts, setWebhookAlerts] = useState(savedSettings?.webhookAlerts ?? true);
  const [webhookUrl, setWebhookUrl] = useState(savedSettings?.webhookUrl || 'https://hooks.slack.com/services/T00/B00/XXXX');
  const [soundAlerts, setSoundAlerts] = useState(savedSettings?.soundAlerts ?? false);
  const [dailyDigest, setDailyDigest] = useState(savedSettings?.dailyDigest ?? true);
  const [webhookPingStatus, setWebhookPingStatus] = useState<string | null>(null);

  // Preferences States
  const [defaultThreshold, setDefaultThreshold] = useState(savedSettings?.defaultThreshold ?? 85);
  const [exportStandard, setExportStandard] = useState(savedSettings?.exportStandard || 'SHA256-Digest');
  const [themeMode, setThemeMode] = useState(savedSettings?.themeMode || 'Cyber Dark (Default)');
  const [timezone, setTimezone] = useState(savedSettings?.timezone || 'UTC (Coordinated Universal Time)');
  const [autoCache, setAutoCache] = useState(savedSettings?.autoCache ?? true);

  // UI Feedback
  const [savedBanner, setSavedBanner] = useState(false);

  const saveToStorage = (updates: any) => {
    const current = {
      name,
      email,
      agency,
      bio,
      apiKey,
      twoFactor,
      emailAlerts,
      webhookAlerts,
      webhookUrl,
      soundAlerts,
      dailyDigest,
      defaultThreshold,
      exportStandard,
      themeMode,
      timezone,
      autoCache,
      ...updates,
    };
    localStorage.setItem('analyst_settings', JSON.stringify(current));
    setSavedBanner(true);
    setTimeout(() => setSavedBanner(false), 2500);
  };

  const handleProfileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    saveToStorage({ name, email, agency, bio });
  };

  const handlePasswordChange = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword && newPassword === confirmPassword) {
      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(false), 3000);
    } else {
      alert('Passwords do not match.');
    }
  };

  const handleRegenerateKey = () => {
    const newKey = 'vm_live_' + Array.from({ length: 28 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
    setApiKey(newKey);
    saveToStorage({ apiKey: newKey });
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleTestWebhook = async () => {
    if (!webhookUrl || !webhookUrl.startsWith('http')) {
      setWebhookPingStatus('Please enter a valid HTTP/HTTPS webhook endpoint URL.');
      setTimeout(() => setWebhookPingStatus(null), 3000);
      return;
    }
    setWebhookPingStatus('Testing webhook connection from browser client...');
    try {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: 'truthlens_ping',
          timestamp: new Date().toISOString(),
          message: 'TruthLens webhook test ping',
        }),
        mode: 'no-cors',
      });
      setWebhookPingStatus('Test webhook payload dispatched from browser client.');
      setTimeout(() => setWebhookPingStatus(null), 3500);
    } catch (err: any) {
      setWebhookPingStatus(`Webhook transmission error: ${err?.message || 'Network request failed'}`);
      setTimeout(() => setWebhookPingStatus(null), 4000);
    }
  };

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to end your active forensic analyst session?')) {
      logout();
      navigate('/login');
    }
  };

  return (
    <div className="page-container">
      {/* Header with Quick Logout Button */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.75rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.025em' }}>
            Platform Configuration & Identity Settings
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Manage authenticated analyst profiles, access security, automated notification webhooks, and forensic engine defaults.
          </p>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            color: '#f87171',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            borderRadius: '8px',
            padding: '0.6rem 1.25rem',
            fontSize: '0.85rem',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.25)')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.12)')}
        >
          <LogOut size={16} />
          <span>Sign Out / Log Out</span>
        </button>
      </div>

      <div style={{ maxWidth: '840px', margin: '0 auto' }}>
        <div className="forensic-card" style={{ padding: '2rem' }}>
          {/* Notification banner on save */}
          {savedBanner && (
            <div
              style={{
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                color: '#86efac',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '1.5rem',
              }}
            >
              <Check size={16} />
              <span>Platform configuration settings successfully updated and saved to local profile.</span>
            </div>
          )}

          {/* Sub-Tabs Navigation */}
          <div
            style={{
              display: 'flex',
              gap: '0.5rem',
              backgroundColor: 'var(--bg-dark)',
              padding: '4px',
              borderRadius: '10px',
              border: '1px solid var(--border-color)',
              marginBottom: '2rem',
              overflowX: 'auto',
            }}
          >
            {[
              { id: 'Profile', label: 'Analyst Profile', icon: User },
              { id: 'Security', label: 'Security & Access', icon: Shield },
              { id: 'Notifications', label: 'Alerts & Webhooks', icon: Bell },
              { id: 'Preferences', label: 'Forensic Engine Defaults', icon: Sliders },
            ].map((tab) => {
              const Icon = tab.icon;
              const isSelected = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id as any)}
                  style={{
                    flex: '1 1 auto',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    background: isSelected ? 'var(--bg-surface)' : 'transparent',
                    color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                    border: isSelected ? '1px solid var(--accent-blue)' : '1px solid transparent',
                    borderRadius: '8px',
                    padding: '0.65rem 1rem',
                    fontWeight: isSelected ? 700 : 500,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <Icon size={16} color={isSelected ? 'var(--accent-blue)' : 'var(--text-muted)'} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* ======================================================== */}
          {/* TAB 1: PROFILE */}
          {/* ======================================================== */}
          {activeTab === 'Profile' && (
            <form onSubmit={handleProfileSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Profile Avatar Header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', paddingBottom: '1.25rem', borderBottom: '1px solid var(--border-color)' }}>
                <div
                  style={{
                    width: '64px',
                    height: '64px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    border: '2px solid var(--accent-blue)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.5rem',
                    fontWeight: 800,
                    color: '#93c5fd',
                  }}
                >
                  {name.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#ffffff' }}>{name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{email}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.35rem' }}>
                    <span className="badge badge-real" style={{ fontSize: '0.65rem' }}>
                      <Shield size={10} /> Authenticated Session
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>
                      User ID: #{user?.user_id || 1}
                    </span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Full Legal / Official Name
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    style={{
                      width: '100%',
                      backgroundColor: 'var(--bg-dark)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '0.65rem 1rem',
                      color: '#ffffff',
                      fontSize: '0.85rem',
                      outline: 'none',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                    Authenticated Analyst Email (JWT Identity #{user?.user_id || 1})
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    style={{
                      width: '100%',
                      backgroundColor: 'var(--bg-dark)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '0.65rem 1rem',
                      color: '#ffffff',
                      fontSize: '0.85rem',
                      outline: 'none',
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                  Forensic Agency / Department
                </label>
                <input
                  type="text"
                  value={agency}
                  onChange={(e) => setAgency(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-dark)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '0.65rem 1rem',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                  Professional Forensic Bio & Expertise
                </label>
                <textarea
                  rows={2}
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-dark)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '0.65rem 1rem',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    outline: 'none',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button type="submit" className="btn-primary" style={{ padding: '0.75rem 1.75rem' }}>
                  <Check size={16} />
                  <span>Update Profile Information</span>
                </button>
              </div>
            </form>
          )}

          {/* ======================================================== */}
          {/* TAB 2: SECURITY & ACCESS */}
          {/* ======================================================== */}
          {activeTab === 'Security' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              {/* Change Password Form */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Lock size={18} color="var(--accent-blue)" />
                    <span>Analyst Account Password</span>
                  </div>
                  <span
                    style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      backgroundColor: 'rgba(148, 163, 184, 0.15)',
                      color: '#94a3b8',
                      border: '1px solid rgba(148, 163, 184, 0.3)',
                    }}
                  >
                    Database Admin Managed
                  </span>
                </div>

                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                  In the current self-hosted SQLite backend, user passwords are encrypted using Werkzeug/scrypt. Direct password resets are administered via the server CLI or database management.
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                      Current Password
                    </label>
                    <input
                      type="password"
                      placeholder="••••••••"
                      disabled
                      value="••••••••••••"
                      style={{
                        width: '100%',
                        backgroundColor: 'var(--bg-dark)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '6px',
                        padding: '0.6rem 0.85rem',
                        color: 'var(--text-muted)',
                        fontSize: '0.85rem',
                        outline: 'none',
                        cursor: 'not-allowed',
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                      New Password
                    </label>
                    <input
                      type="password"
                      placeholder="••••••••"
                      disabled
                      value=""
                      style={{
                        width: '100%',
                        backgroundColor: 'var(--bg-dark)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '6px',
                        padding: '0.6rem 0.85rem',
                        color: 'var(--text-muted)',
                        fontSize: '0.85rem',
                        outline: 'none',
                        cursor: 'not-allowed',
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                      Confirm Password
                    </label>
                    <input
                      type="password"
                      placeholder="••••••••"
                      disabled
                      value=""
                      style={{
                        width: '100%',
                        backgroundColor: 'var(--bg-dark)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '6px',
                        padding: '0.6rem 0.85rem',
                        color: 'var(--text-muted)',
                        fontSize: '0.85rem',
                        outline: 'none',
                        cursor: 'not-allowed',
                      }}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    disabled
                    className="btn-secondary"
                    style={{ alignSelf: 'flex-start', padding: '0.5rem 1.25rem', fontSize: '0.8rem', opacity: 0.6, cursor: 'not-allowed' }}
                    title="Self-hosted backend does not expose a public password-reset endpoint."
                  >
                    <span>Password Reset (Admin CLI Only)</span>
                  </button>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    No public password-change endpoint is exposed on the backend.
                  </span>
                </div>
              </div>

              {/* API Key Management */}
              <div style={{ backgroundColor: 'var(--bg-dark)', borderRadius: '10px', padding: '1.25rem', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', fontWeight: 700, color: '#ffffff' }}>
                    <Key size={16} color="var(--accent-cyan)" />
                    <span>Client Identification Secret</span>
                    <span
                      style={{
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '9999px',
                        backgroundColor: 'rgba(148, 163, 184, 0.15)',
                        color: '#94a3b8',
                        border: '1px solid rgba(148, 163, 184, 0.3)',
                      }}
                    >
                      Client-Side Only
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleRegenerateKey}
                    className="btn-secondary"
                    style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                  >
                    <RotateCcw size={13} />
                    <span>Regenerate Key</span>
                  </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#93c5fd', backgroundColor: '#070a12', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1px solid #1e293b', wordBreak: 'break-all' }}>
                  <span>{apiKey}</span>
                  <button
                    type="button"
                    onClick={handleCopyKey}
                    style={{ background: 'none', border: 'none', color: 'var(--accent-cyan)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="Copy Key"
                  >
                    {copiedKey ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                    <span style={{ fontSize: '0.7rem' }}>{copiedKey ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                  Backend API routes strictly authenticate requests using JWT Bearer tokens. This client key is retained for local script and client identification.
                </div>
              </div>

              {/* Hardware 2FA */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem 1.25rem', backgroundColor: 'var(--bg-dark)', borderRadius: '10px', border: '1px solid var(--border-color)', gap: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Shield size={20} color="var(--accent-green)" />
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>Hardware Security Key (FIDO2 / WebAuthn)</div>
                      <span
                        style={{
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '9999px',
                          backgroundColor: 'rgba(234, 179, 8, 0.15)',
                          color: '#facc15',
                          border: '1px solid rgba(234, 179, 8, 0.3)',
                        }}
                      >
                        Planned Specification
                      </span>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      Physical security key integration is planned for future releases. Current authentication is secured via JWT.
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  disabled
                  checked={false}
                  title="Hardware 2FA is not implemented in the current backend"
                  style={{ width: '18px', height: '18px', opacity: 0.5, cursor: 'not-allowed' }}
                />
              </div>

              {/* Active Sessions */}
              <div style={{ backgroundColor: 'var(--bg-dark)', borderRadius: '10px', padding: '1.25rem', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.75rem' }}>
                  Active Analyst Device Sessions
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.5rem 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Laptop size={18} color="var(--accent-blue)" />
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#ffffff' }}>Windows 11 (Chrome 128) • Current Session</div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Localhost socket (127.0.0.1:5173) • Active Now</div>
                    </div>
                  </div>
                  <span className="badge badge-real">Current Device</span>
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB 3: NOTIFICATIONS & WEBHOOKS */}
          {/* ======================================================== */}
          {activeTab === 'Notifications' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Bell size={18} color="var(--accent-blue)" />
                <span>Automated Incident Dispatch & Alert Routing</span>
              </div>

              {/* Email Alerts Toggle */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.25rem', backgroundColor: 'var(--bg-dark)', borderRadius: '10px', border: '1px solid var(--border-color)', gap: '1rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>Automated Threat Email Dispatch</div>
                    <span
                      style={{
                        fontSize: '0.65rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '9999px',
                        backgroundColor: 'rgba(148, 163, 184, 0.15)',
                        color: '#94a3b8',
                        border: '1px solid rgba(148, 163, 184, 0.3)',
                      }}
                    >
                      No SMTP Configured
                    </span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Outbound SMTP relay is not configured in this local deployment. Direct email alerts are currently offline.
                  </div>
                </div>
                <input
                  type="checkbox"
                  disabled
                  checked={false}
                  title="No outbound SMTP relay is configured in the current backend"
                  style={{ width: '18px', height: '18px', opacity: 0.5, cursor: 'not-allowed' }}
                />
              </div>

              {/* Sound Alerts */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.25rem', backgroundColor: 'var(--bg-dark)', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Volume2 size={18} color="var(--accent-amber)" />
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>Audio Alert Chime on Detection</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Client-side audio notification preference stored in browser session.
                    </div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={soundAlerts}
                  onChange={(e) => {
                    setSoundAlerts(e.target.checked);
                    saveToStorage({ soundAlerts: e.target.checked });
                  }}
                  style={{ width: '18px', height: '18px', accentColor: 'var(--accent-blue)', cursor: 'pointer' }}
                />
              </div>

              {/* Webhook Configuration */}
              <div style={{ backgroundColor: 'var(--bg-dark)', borderRadius: '10px', padding: '1.25rem', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>Incident Webhook Relay (Slack / Discord / SIEM)</div>
                      <span
                        style={{
                          fontSize: '0.65rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '9999px',
                          backgroundColor: 'rgba(148, 163, 184, 0.15)',
                          color: '#94a3b8',
                          border: '1px solid rgba(148, 163, 184, 0.3)',
                        }}
                      >
                        Client-Side Forwarding
                      </span>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Forward incident alert payloads directly from the browser client to your webhook endpoint.</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={webhookAlerts}
                    onChange={(e) => {
                      setWebhookAlerts(e.target.checked);
                      saveToStorage({ webhookAlerts: e.target.checked });
                    }}
                    style={{ width: '18px', height: '18px', accentColor: 'var(--accent-blue)', cursor: 'pointer' }}
                  />
                </div>

                {webhookAlerts && (
                  <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <input
                        type="url"
                        value={webhookUrl}
                        onChange={(e) => setWebhookUrl(e.target.value)}
                        placeholder="https://hooks.slack.com/services/..."
                        style={{
                          flex: 1,
                          backgroundColor: 'var(--bg-card)',
                          border: '1px solid var(--border-color)',
                          borderRadius: '6px',
                          padding: '0.5rem 0.75rem',
                          color: '#ffffff',
                          fontSize: '0.8rem',
                          outline: 'none',
                        }}
                      />
                      <button
                        type="button"
                        onClick={handleTestWebhook}
                        className="btn-secondary"
                        style={{ padding: '0.5rem 1rem', fontSize: '0.75rem' }}
                      >
                        <Zap size={13} />
                        <span>Test Ping</span>
                      </button>
                    </div>
                    {webhookPingStatus && (
                      <div style={{ fontSize: '0.75rem', color: webhookPingStatus.includes('error') ? '#fca5a5' : 'var(--accent-green)', fontFamily: 'var(--font-mono)' }}>
                        {webhookPingStatus}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* TAB 4: PREFERENCES & FORENSIC ENGINE DEFAULTS */}
          {/* ======================================================== */}
          {activeTab === 'Preferences' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sliders size={18} color="var(--accent-blue)" />
                <span>Forensic Engine Defaults & Thresholds</span>
              </div>

              {/* Threshold Slider */}
              <div style={{ backgroundColor: 'var(--bg-dark)', borderRadius: '10px', padding: '1.25rem', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>
                    Forensic Risk Triage Threshold
                  </label>
                  <span style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--accent-blue)' }}>
                    {defaultThreshold}%
                  </span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="99"
                  value={defaultThreshold}
                  onChange={(e) => {
                    setDefaultThreshold(Number(e.target.value));
                    saveToStorage({ defaultThreshold: Number(e.target.value) });
                  }}
                  style={{ width: '100%', accentColor: 'var(--accent-blue)', cursor: 'pointer' }}
                />
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                  Media analyses scoring above this confidence level are flagged as high risk for analyst triage and abuse reporting.
                </div>
              </div>

              {/* Forensic Standard */}
              <div style={{ backgroundColor: 'var(--bg-dark)', borderRadius: '10px', padding: '1.25rem', border: '1px solid var(--border-color)' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#ffffff', marginBottom: '0.5rem' }}>
                  Default Forensic Evidence Export Format
                </label>
                <select
                  value={exportStandard}
                  onChange={(e) => {
                    setExportStandard(e.target.value);
                    saveToStorage({ exportStandard: e.target.value });
                  }}
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '0.65rem 1rem',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                >
                  <option value="SHA256-Digest">SHA-256 Cryptographic Evidence Digest (TruthLens Native)</option>
                  <option value="JSON-Forensic">Structured JSON Evidence Record (ISO/IEC 27037 compliant)</option>
                  <option value="PDF-Summary">PDF Forensic Evidence Dossier Summary</option>
                </select>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                  Primary evidence digest and serialization format used for local reports and dossier export packages.
                </div>
              </div>

              {/* Timezone */}
              <div style={{ backgroundColor: 'var(--bg-dark)', borderRadius: '10px', padding: '1.25rem', border: '1px solid var(--border-color)' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#ffffff', marginBottom: '0.5rem' }}>
                  Evidence Timestamp Timezone
                </label>
                <select
                  value={timezone}
                  onChange={(e) => {
                    setTimezone(e.target.value);
                    saveToStorage({ timezone: e.target.value });
                  }}
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '0.65rem 1rem',
                    color: '#ffffff',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                >
                  <option value="UTC (Coordinated Universal Time)">UTC (Coordinated Universal Time)</option>
                  <option value="EST (Eastern Standard Time)">EST (Eastern Standard Time - New York)</option>
                  <option value="PST (Pacific Standard Time)">PST (Pacific Standard Time - San Francisco)</option>
                  <option value="GMT (Greenwich Mean Time)">GMT (London / Dublin)</option>
                  <option value="IST (Indian Standard Time)">IST (New Delhi / Mumbai)</option>
                </select>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                  Timezone formatting applied to recorded scan timestamps and forensic reports.
                </div>
              </div>
            </div>
          )}

          {/* ======================================================== */}
          {/* DEDICATED LOGOUT / SESSION TERMINATION SECTION */}
          {/* ======================================================== */}
          <div
            style={{
              marginTop: '2.5rem',
              paddingTop: '1.75rem',
              borderTop: '1px solid var(--border-color)',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '1rem',
            }}
          >
            <div>
              <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#ffffff' }}>
                Session & Authentication Management
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Terminate active cryptographic session and return to the analyst login portal.
              </div>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                backgroundColor: '#ef4444',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                padding: '0.7rem 1.5rem',
                fontSize: '0.875rem',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 12px rgba(239, 68, 68, 0.4)',
                transition: 'all 0.15s ease',
              }}
            >
              <LogOut size={16} />
              <span>Log Out</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
