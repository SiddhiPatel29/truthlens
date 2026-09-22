import React, { useState } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle2, RotateCcw, Sliders } from 'lucide-react';

export const RiskAssessment: React.FC = () => {
  // Configurable risk factor values
  const [factors, setFactors] = useState([
    { key: 'ai', label: 'AI Confidence Score', weight: 0.35, percent: 98, level: 'CRITICAL', color: '#ef4444' },
    { key: 'face', label: 'Spatial Artifact Anomaly (Forensic Heatmap)', weight: 0.25, percent: 95, level: 'HIGH', color: '#ef4444' },
    { key: 'temporal', label: 'Temporal Sequence Inconsistency', weight: 0.20, percent: 88, level: 'HIGH', color: '#ef4444' },
    { key: 'lipsync', label: 'Cross-Modal Consistency Indicator', weight: 0.12, percent: 61, level: 'MEDIUM', color: '#f59e0b' },
    { key: 'metadata', label: 'EXIF & C2PA Provenance Anomaly', weight: 0.08, percent: 24, level: 'LOW', color: '#10b981' },
  ]);

  const [isCustomizing, setIsCustomizing] = useState(false);

  // Calculate composite weighted risk percentage
  const compositeScore = Math.round(
    factors.reduce((acc, curr) => acc + curr.percent * curr.weight, 0)
  );

  const getThreatClassification = (score: number) => {
    if (score >= 80) return { title: 'OVERALL RISK: CRITICAL', badge: 'ACTION MANDATORY', bg: 'rgba(239, 68, 68, 0.12)', border: 'rgba(239, 68, 68, 0.4)', color: '#ef4444', text: '#fca5a5' };
    if (score >= 60) return { title: 'OVERALL RISK: HIGH', badge: 'ELEVATED THREAT', bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.4)', color: '#f59e0b', text: '#fde68a' };
    if (score >= 40) return { title: 'OVERALL RISK: MODERATE', badge: 'MANUAL REVIEW', bg: 'rgba(59, 130, 246, 0.12)', border: 'rgba(59, 130, 246, 0.4)', color: '#3b82f6', text: '#93c5fd' };
    return { title: 'OVERALL RISK: LOW', badge: 'BENIGN CONTENT', bg: 'rgba(16, 185, 129, 0.12)', border: 'rgba(16, 185, 129, 0.4)', color: '#10b981', text: '#86efac' };
  };

  const threat = getThreatClassification(compositeScore);

  const handleSliderChange = (index: number, newPercent: number) => {
    setFactors((prev) =>
      prev.map((f, i) => {
        if (i !== index) return f;
        let color = '#10b981';
        let level = 'LOW';
        if (newPercent >= 75) {
          color = '#ef4444';
          level = 'HIGH';
        } else if (newPercent >= 50) {
          color = '#f59e0b';
          level = 'MEDIUM';
        }
        return { ...f, percent: newPercent, color, level };
      })
    );
  };

  const resetDefaults = () => {
    setFactors([
      { key: 'ai', label: 'AI Confidence Score', weight: 0.35, percent: 98, level: 'CRITICAL', color: '#ef4444' },
      { key: 'face', label: 'Spatial Artifact Anomaly (Forensic Heatmap)', weight: 0.25, percent: 95, level: 'HIGH', color: '#ef4444' },
      { key: 'temporal', label: 'Temporal Sequence Inconsistency', weight: 0.20, percent: 88, level: 'HIGH', color: '#ef4444' },
      { key: 'lipsync', label: 'Cross-Modal Consistency Indicator', weight: 0.12, percent: 61, level: 'MEDIUM', color: '#f59e0b' },
      { key: 'metadata', label: 'EXIF & C2PA Provenance Anomaly', weight: 0.08, percent: 24, level: 'LOW', color: '#10b981' },
    ]);
  };

  return (
    <div className="forensic-card" style={{ padding: '1.75rem', marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
        <div>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>
            Multi-Factor Forensic Risk Assessment
          </h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Weighted aggregation across spatial artifacts, temporal consistency, cross-modal indicators, and metadata structure.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            type="button"
            onClick={() => setIsCustomizing(!isCustomizing)}
            className="btn-secondary"
            style={{ padding: '4px 10px', fontSize: '0.75rem' }}
          >
            <Sliders size={13} />
            <span>{isCustomizing ? 'Hide Sliders' : 'Adjust Weights & Factors'}</span>
          </button>
          {isCustomizing && (
            <button
              type="button"
              onClick={resetDefaults}
              className="btn-secondary"
              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
              title="Reset to defaults"
            >
              <RotateCcw size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Factors Severity Bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '2rem' }}>
        {factors.map((f, idx) => (
          <div key={f.key}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.4rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                {f.label} <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>({Math.round(f.weight * 100)}% wt)</span>
              </span>
              <span style={{ color: f.color }}>
                {f.percent}% • {f.level}
              </span>
            </div>

            {isCustomizing ? (
              <input
                type="range"
                min="0"
                max="100"
                value={f.percent}
                onChange={(e) => handleSliderChange(idx, Number(e.target.value))}
                style={{ width: '100%', accentColor: f.color, cursor: 'pointer' }}
              />
            ) : (
              <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-dark)', borderRadius: '4px', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${f.percent}%`,
                    height: '100%',
                    backgroundColor: f.color,
                    borderRadius: '4px',
                    boxShadow: `0 0 8px ${f.color}80`,
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Dynamic Overall Risk Banner Card */}
      <div
        style={{
          backgroundColor: threat.bg,
          border: `1px solid ${threat.border}`,
          borderRadius: '10px',
          padding: '1.25rem 1.5rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          transition: 'all 0.3s ease',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              padding: '8px',
              borderRadius: '8px',
              backgroundColor: threat.color,
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <ShieldAlert size={24} />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              Threat Classification ({compositeScore}/100 Composite Score)
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 900, color: threat.text }}>
              {threat.title}
            </div>
          </div>
        </div>

        <span
          className="badge"
          style={{
            backgroundColor: threat.color,
            color: '#ffffff',
            fontSize: '0.85rem',
            padding: '0.4rem 1rem',
            fontWeight: 700,
          }}
        >
          {threat.badge}
        </span>
      </div>
    </div>
  );
};
