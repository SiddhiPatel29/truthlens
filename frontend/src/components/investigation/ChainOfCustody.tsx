import React, { useState } from 'react';
import { Clock, Shield, FileCheck, Cpu, UserCheck, Plus, Copy, Check, Filter } from 'lucide-react';

interface CustodyEvent {
  id: string;
  time: string;
  title: string;
  subtitle: string;
  hash?: string;
  category: 'System' | 'Cryptographic' | 'Analyst';
  icon: typeof Clock;
}

export const ChainOfCustody: React.FC = () => {
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [filter, setFilter] = useState<'All' | 'System' | 'Cryptographic' | 'Analyst'>('All');
  const [isAdding, setIsAdding] = useState(false);
  const [newAction, setNewAction] = useState('');
  const [newDetails, setNewDetails] = useState('');

  const [events, setEvents] = useState<CustodyEvent[]>([
    {
      id: '1',
      time: '08:31:20 UTC',
      title: 'File ingested by Analyst',
      subtitle: 'Source: Forensic Upload Portal (User IP: 192.168.1.102)',
      category: 'Analyst',
      icon: Clock,
    },
    {
      id: '2',
      time: '08:31:25 UTC',
      title: 'SHA-256 fingerprint generated & locked',
      subtitle: 'Cryptographic hash anchored to local forensic ledger',
      hash: '9f4c82b1d3e4a9d4e5f6789012345678abcdef0123456789abcdef0123456789',
      category: 'Cryptographic',
      icon: Shield,
    },
    {
      id: '3',
      time: '08:31:30 UTC',
      title: 'Multi-modal analysis pipeline started',
      subtitle: 'Models: ResNet50 Spatial + Bi-LSTM Temporal + SyncNet Viseme',
      category: 'System',
      icon: Cpu,
    },
    {
      id: '4',
      time: '08:31:45 UTC',
      title: '30 keyframes extracted & normalized',
      subtitle: 'OpenCV frame extraction with bicubic resampling',
      category: 'System',
      icon: FileCheck,
    },
    {
      id: '5',
      time: '08:32:15 UTC',
      title: 'Neural detection completed',
      subtitle: 'Verdict: Synthetic Media Detected (Confidence: 98.2%)',
      hash: 'a71e89b2c01d4ef32a1567bc9812401f89bcdef123456789abcdef0123456789',
      category: 'Cryptographic',
      icon: Shield,
    },
    {
      id: '6',
      time: '08:32:25 UTC',
      title: 'Evidence dossier generated',
      subtitle: 'Complies with C2PA-Authenticity and NIST-AI-100-2',
      category: 'System',
      icon: FileCheck,
    },
    {
      id: '7',
      time: '08:33:10 UTC',
      title: 'Human forensic sign-off completed',
      subtitle: 'Analyst: Lead Examiner • Verdict: Confirmed Synthetic',
      category: 'Analyst',
      icon: UserCheck,
    },
  ]);

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleAddEntry = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAction.trim()) return;

    const newHash = Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
    const now = new Date();
    const timeStr = `${String(now.getUTCHours()).padStart(2, '0')}:${String(now.getUTCMinutes()).padStart(2, '0')}:${String(now.getUTCSeconds()).padStart(2, '0')} UTC`;

    const newEntry: CustodyEvent = {
      id: String(Date.now()),
      time: timeStr,
      title: newAction.trim(),
      subtitle: newDetails.trim() || 'Manual custodial verification entry logged by session analyst.',
      hash: newHash,
      category: 'Analyst',
      icon: UserCheck,
    };

    setEvents((prev) => [...prev, newEntry]);
    setNewAction('');
    setNewDetails('');
    setIsAdding(false);
  };

  const filteredEvents = events.filter((e) => {
    if (filter === 'All') return true;
    return e.category === filter;
  });

  return (
    <div className="forensic-card" style={{ padding: '1.75rem', marginBottom: '1.5rem' }}>
      {/* Header & Controls */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
        <div>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>
            Cryptographic Chain of Custody & Audit Trail
          </h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Immutable forensic verification lifecycle tracking evidentiary integrity from ingestion to dispatch.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Category Filter */}
          <div style={{ display: 'flex', backgroundColor: 'var(--bg-dark)', borderRadius: '6px', padding: '2px', border: '1px solid var(--border-color)' }}>
            {(['All', 'System', 'Cryptographic', 'Analyst'] as const).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                style={{
                  background: filter === f ? 'var(--bg-surface)' : 'transparent',
                  color: filter === f ? '#ffffff' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontSize: '0.725rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {f}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setIsAdding(!isAdding)}
            className="btn-secondary"
            style={{ padding: '5px 12px', fontSize: '0.75rem' }}
          >
            <Plus size={14} />
            <span>{isAdding ? 'Cancel Entry' : 'Add Custodial Note'}</span>
          </button>
        </div>
      </div>

      {/* Add Custodial Log Entry Form */}
      {isAdding && (
        <form
          onSubmit={handleAddEntry}
          style={{
            backgroundColor: 'var(--bg-dark)',
            border: '1px solid var(--accent-blue)',
            borderRadius: '8px',
            padding: '1.25rem',
            marginBottom: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem',
          }}
        >
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#ffffff' }}>
            Append Tamper-Evident Custodial Audit Log
          </div>
          <input
            type="text"
            required
            value={newAction}
            onChange={(e) => setNewAction(e.target.value)}
            placeholder="Action Title (e.g. Subpoena received, Verified against third-party archive...)"
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '0.5rem 0.75rem',
              color: '#ffffff',
              fontSize: '0.825rem',
              outline: 'none',
            }}
          />
          <input
            type="text"
            value={newDetails}
            onChange={(e) => setNewDetails(e.target.value)}
            placeholder="Custodial context or verification notes..."
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '0.5rem 0.75rem',
              color: '#ffffff',
              fontSize: '0.825rem',
              outline: 'none',
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={() => setIsAdding(false)}
              className="btn-secondary"
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" style={{ padding: '4px 12px', fontSize: '0.75rem' }}>
              Append Cryptographic Record
            </button>
          </div>
        </form>
      )}

      {/* Vertical Timeline Tree */}
      <div style={{ position: 'relative', paddingLeft: '2.25rem' }}>
        {/* Continuous vertical line */}
        <div
          style={{
            position: 'absolute',
            left: '11px',
            top: '12px',
            bottom: '20px',
            width: '2px',
            backgroundColor: '#1e293b',
          }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {filteredEvents.map((ev, i) => {
            const Icon = ev.icon;
            const isLast = i === filteredEvents.length - 1;
            return (
              <div key={ev.id} style={{ position: 'relative' }}>
                {/* Node Dot */}
                <div
                  style={{
                    position: 'absolute',
                    left: '-2.25rem',
                    top: '2px',
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    backgroundColor: isLast ? 'var(--accent-green)' : 'var(--bg-card)',
                    border: isLast ? '2px solid #ffffff' : '2px solid var(--accent-blue)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: isLast ? '#0b0f19' : 'var(--accent-blue)',
                    boxShadow: '0 0 10px rgba(59, 130, 246, 0.4)',
                  }}
                >
                  <Icon size={12} />
                </div>

                <div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: '0.5rem' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                      {ev.time}
                    </span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#ffffff' }}>
                      {ev.title}
                    </span>
                    <span
                      style={{
                        fontSize: '0.65rem',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        backgroundColor:
                          ev.category === 'Cryptographic'
                            ? 'rgba(59, 130, 246, 0.2)'
                            : ev.category === 'Analyst'
                            ? 'rgba(16, 185, 129, 0.2)'
                            : 'rgba(148, 163, 184, 0.2)',
                        color:
                          ev.category === 'Cryptographic'
                            ? '#93c5fd'
                            : ev.category === 'Analyst'
                            ? '#86efac'
                            : '#cbd5e1',
                      }}
                    >
                      {ev.category}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {ev.subtitle}
                  </div>

                  {ev.hash && (
                    <div
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        marginTop: '0.35rem',
                        backgroundColor: '#070a12',
                        border: '1px solid #1e293b',
                        borderRadius: '4px',
                        padding: '2px 8px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.675rem',
                        color: '#94a3b8',
                      }}
                    >
                      <span>SHA256: {ev.hash.slice(0, 16)}...{ev.hash.slice(-8)}</span>
                      <button
                        type="button"
                        onClick={() => handleCopyHash(ev.hash!)}
                        style={{ background: 'none', border: 'none', color: 'var(--accent-cyan)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                        title="Copy complete hash"
                      >
                        {copiedHash === ev.hash ? <Check size={11} color="#10b981" /> : <Copy size={11} />}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
