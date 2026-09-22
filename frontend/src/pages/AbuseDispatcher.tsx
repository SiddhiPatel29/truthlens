import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { dispatchAbuseReport } from '../api/abuse';
import { AlertTriangle, CheckCircle, Send, Globe, Youtube, Twitter, Instagram, ShieldCheck, Loader2 } from 'lucide-react';

export const AbuseDispatcher: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [platform, setPlatform] = useState<'youtube' | 'x' | 'meta' | 'custom'>('youtube');
  const [targetUrl, setTargetUrl] = useState('https://youtube.com/watch?v=deepfake_evidence_00821');
  const [category, setCategory] = useState('Synthetic Impersonation & Manipulated Media');
  const [analystNotes, setAnalystNotes] = useState(
    searchParams.get('notes') ||
      'Automated synthetic media detection flagged visual/acoustic anomalies with elevated confidence.'
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rawConf = searchParams.get('confidence');
  const confidence = rawConf ? (Number(rawConf) > 1 ? Number(rawConf) / 100 : Number(rawConf)) : 0.85;

  const scanIdParam = searchParams.get('scanId') || searchParams.get('scan_id');
  const scanIdNum = scanIdParam ? parseInt(scanIdParam, 10) : undefined;

  const platforms = [
    { id: 'youtube', label: 'YouTube', icon: Youtube, color: '#ef4444' },
    { id: 'x', label: 'X (Twitter)', icon: Twitter, color: '#38bdf8' },
    { id: 'meta', label: 'Instagram / Meta', icon: Instagram, color: '#ec4899' },
    { id: 'custom', label: 'Enterprise Webhook', icon: Globe, color: '#8b5cf6' },
  ] as const;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!targetUrl.trim()) 
    {
      setError('Target URL is required for platform dispatch.');
      return;
    }

    setLoading(true);
    try 
    {
      const res = await dispatchAbuseReport({
        platform,
        target_url: targetUrl,
        category,
        confidence_score: confidence,
        analyst_notes: analystNotes,
        ...(scanIdNum && !isNaN(scanIdNum) ? { scan_id: scanIdNum } : {}),
      });

      if (res.success && res.data) 
      {
        sessionStorage.setItem('current_dossier_receipt', JSON.stringify(res.data));
        navigate(`/reports?reportId=${res.data.report_id}`);
      } 
      else 
      {
        throw new Error(res.message || 'Failed to dispatch report.');
      }
    } 
    catch (err: any) 
    {
      setError(err.message || 'Dispatch failed. Verify the backend connection.');
    } 
    finally 
    {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.025em' }}>
          Abuse Dispatcher & Takedown Relay
        </h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Compile cryptographically hashed takedown dossiers formatted for major platform Trust & Safety escalation channels.
        </p>
      </div>

      <div style={{ maxWidth: '860px', margin: '0 auto' }}>
        <div className="forensic-card" style={{ padding: '2rem' }}>
          {error && (
            <div
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: '#fca5a5',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '1.5rem',
              }}
            >
              <AlertTriangle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Target Platform Selector (Frame 16) */}
            <div>
              <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                Select Target Social Platform:
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                {platforms.map((p) => {
                  const Icon = p.icon;
                  const isSelected = platform === p.id;
                  return (
                    <button
                      type="button"
                      key={p.id}
                      onClick={() => setPlatform(p.id)}
                      style={{
                        padding: '0.85rem',
                        borderRadius: '10px',
                        border: isSelected ? `2px solid ${p.color}` : '1px solid var(--border-color)',
                        backgroundColor: isSelected ? 'var(--bg-surface)' : 'var(--bg-dark)',
                        color: isSelected ? '#ffffff' : 'var(--text-secondary)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.6rem',
                        fontWeight: 600,
                        fontSize: '0.85rem',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <Icon size={18} color={p.color} />
                      <span>{p.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Target URL */}
            <div>
              <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                Infringing Content URL / Link:
              </label>
              <input
                type="url"
                required
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                placeholder="https://..."
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

            {/* Violation Category */}
            <div>
              <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                Forensic Violation Category:
              </label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
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

            {/* Analyst Notes */}
            <div>
              <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
                Escalation Evidence Notes:
              </label>
              <textarea
                rows={3}
                value={analystNotes}
                onChange={(e) => setAnalystNotes(e.target.value)}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--bg-dark)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '0.75rem 1rem',
                  color: '#ffffff',
                  fontSize: '0.85rem',
                  outline: 'none',
                  fontFamily: 'inherit',
                }}
              />
            </div>

            {/* Reporting Eligibility Card (Frame 16) */}
            <div
              style={{
                backgroundColor: 'var(--bg-dark)',
                borderRadius: '8px',
                padding: '1rem',
                border: '1px solid var(--border-color)',
              }}
            >
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                Platform Takedown Eligibility Gate
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.5rem', fontSize: '0.8rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#86efac' }}>
                  <CheckCircle size={14} /> Above 85% threshold
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#86efac' }}>
                  <CheckCircle size={14} /> Evidence available
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#86efac' }}>
                  <CheckCircle size={14} /> Human review completed
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#86efac' }}>
                  <CheckCircle size={14} /> Rate limit available
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
              style={{ padding: '0.85rem', fontSize: '0.95rem' }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Signing & Dispatching Dossier...</span>
                </>
              ) : (
                <>
                  <ShieldCheck size={18} />
                  <span>Generate Evidence Dossier</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
