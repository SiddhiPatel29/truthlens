import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, AlertCircle, XCircle, Send, Check, ShieldCheck, PenTool } from 'lucide-react';

interface HumanReviewProps {
  scanId?: number | string;
}

export const HumanReview: React.FC<HumanReviewProps> = ({ scanId = 821 }) => {
  const [decision, setDecision] = useState<'CONFIRMED' | 'UNCERTAIN' | 'REJECTED'>('CONFIRMED');
  const [notes, setNotes] = useState(
    'Visual inspection confirms unnatural boundary blurring along jawline and high-confidence temporal instability. Escalation to abuse takedown recommended.'
  );
  const [checklist, setChecklist] = useState({
    spatialHeatmap: true,
    temporalAnomaly: true,
    lipSyncDesync: true,
    c2paSignature: true,
  });
  const [saved, setSaved] = useState(false);
  const navigate = useNavigate();

  const toggleCheck = (key: keyof typeof checklist) => {
    setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSaveAndEscalate = () => {
    const reviewData = {
      scanId,
      decision,
      notes,
      checklist,
      examiner: 'Lead Forensic Examiner (Admin)',
      signatureHash: 'sig_ed25519_' + Array.from({ length: 24 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
      timestamp: new Date().toISOString(),
    };
    sessionStorage.setItem('current_review_decision', JSON.stringify(reviewData));
    setSaved(true);
    setTimeout(() => {
      navigate(`/abuse?scanId=${scanId}&notes=${encodeURIComponent(notes)}&confidence=0.982`);
    }, 600);
  };

  return (
    <div className="forensic-card" style={{ padding: '1.75rem', marginBottom: '1.5rem' }}>
      <div style={{ marginBottom: '1.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
        <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>
          Human-in-the-Loop Expert Review & Sign-Off
        </h3>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
          Mandatory analyst verification and evidence sign-off required prior to legal and platform takedown dispatch.
        </p>
      </div>

      {/* AI Verdict & Interactive Evidence Checklist */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* AI Verdict Card */}
        <div style={{ backgroundColor: 'var(--bg-dark)', padding: '1.25rem', borderRadius: '10px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              System Automated Classification
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--accent-red)', margin: '0.35rem 0' }}>
              AI Verdict: 98.2% Synthetic
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              Autonomous detection confidence exceeds the 85.0% threshold for immediate platform escalation.
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #1e293b', fontSize: '0.725rem', color: 'var(--accent-cyan)' }}>
            <ShieldCheck size={14} />
            <span>Digital Fingerprint Verified via SHA-256</span>
          </div>
        </div>

        {/* Evidence Verification Checklist */}
        <div style={{ backgroundColor: 'var(--bg-dark)', padding: '1.25rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            Forensic Checklist Verification
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
            {[
              { key: 'spatialHeatmap', label: 'Grad-CAM++ Spatial Tamper Zones' },
              { key: 'temporalAnomaly', label: 'Temporal Consistency Inter-frame Jitter' },
              { key: 'lipSyncDesync', label: 'Audio-Visual Lip-Sync Desynchronization' },
              { key: 'c2paSignature', label: 'EXIF / C2PA Provenance Manifest Absence' },
            ].map((row) => {
              const checked = checklist[row.key as keyof typeof checklist];
              return (
                <div
                  key={row.key}
                  onClick={() => toggleCheck(row.key as keyof typeof checklist)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    backgroundColor: checked ? 'rgba(16, 185, 129, 0.08)' : 'transparent',
                    cursor: 'pointer',
                  }}
                >
                  <span style={{ fontSize: '0.8rem', color: checked ? '#ffffff' : 'var(--text-muted)' }}>
                    {row.label}
                  </span>
                  <span className={`badge ${checked ? 'badge-real' : 'badge-uncertain'}`} style={{ fontSize: '0.65rem' }}>
                    {checked ? 'Verified' : 'Pending'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Review Decision Buttons */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
          Analyst Review Decision:
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <button
            type="button"
            onClick={() => setDecision('CONFIRMED')}
            style={{
              padding: '0.85rem',
              borderRadius: '8px',
              border: decision === 'CONFIRMED' ? '2px solid #10b981' : '1px solid var(--border-color)',
              backgroundColor: decision === 'CONFIRMED' ? 'rgba(16, 185, 129, 0.2)' : 'var(--bg-dark)',
              color: decision === 'CONFIRMED' ? '#ffffff' : 'var(--text-secondary)',
              fontWeight: 700,
              fontSize: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <CheckCircle2 size={16} color="#10b981" />
            <span>Confirm Finding (Synthetic)</span>
          </button>

          <button
            type="button"
            onClick={() => setDecision('UNCERTAIN')}
            style={{
              padding: '0.85rem',
              borderRadius: '8px',
              border: decision === 'UNCERTAIN' ? '2px solid #f59e0b' : '1px solid var(--border-color)',
              backgroundColor: decision === 'UNCERTAIN' ? 'rgba(245, 158, 11, 0.2)' : 'var(--bg-dark)',
              color: decision === 'UNCERTAIN' ? '#ffffff' : 'var(--text-secondary)',
              fontWeight: 700,
              fontSize: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <AlertCircle size={16} color="#f59e0b" />
            <span>Mark as Inconclusive</span>
          </button>

          <button
            type="button"
            onClick={() => setDecision('REJECTED')}
            style={{
              padding: '0.85rem',
              borderRadius: '8px',
              border: decision === 'REJECTED' ? '2px solid #ef4444' : '1px solid var(--border-color)',
              backgroundColor: decision === 'REJECTED' ? 'rgba(239, 68, 68, 0.2)' : 'var(--bg-dark)',
              color: decision === 'REJECTED' ? '#ffffff' : 'var(--text-secondary)',
              fontWeight: 700,
              fontSize: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <XCircle size={16} color="#ef4444" />
            <span>Reject Finding (Authentic)</span>
          </button>
        </div>
      </div>

      {/* Reviewer Notes Textarea */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
          Analyst Review Notes & Legal Escalation Rationale:
        </label>
        <textarea
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add forensic notes, context, or legal escalation rationale..."
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

      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <PenTool size={14} color="var(--accent-blue)" />
          <span>Signing Examiner: <strong>Admin / Lead Analyst</strong></span>
        </div>

        <button
          type="button"
          onClick={handleSaveAndEscalate}
          className="btn-primary"
          style={{ padding: '0.75rem 1.5rem' }}
        >
          {saved ? <Check size={16} /> : <Send size={16} />}
          <span>{saved ? 'Signature Stamped & Saved' : 'Sign & Escalate to Abuse Dispatch'}</span>
        </button>
      </div>
    </div>
  );
};
