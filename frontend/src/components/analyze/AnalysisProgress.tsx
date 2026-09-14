import React, { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, Play, Volume2, Maximize2 } from 'lucide-react';

interface AnalysisProgressProps {
  modality: 'video' | 'audio' | 'image' | 'text';
}

export const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ modality }) => {
  const [progress, setProgress] = useState(15);
  const [currentStep, setCurrentStep] = useState(2);

  const steps = [
    { title: 'File integrity verified', detail: 'Cryptographic hash generated' },
    { title: 'SHA-256 fingerprint generated', detail: 'Manifest fingerprint established' },
    { title: 'Frames extracted (30/30)', detail: 'Keyframes decoded via OpenCV' },
    { title: 'Face detection completed', detail: 'Biometric region bounding box locked' },
    { title: 'Spatial analysis (ResNet50)', detail: 'Laplacian edge & texture variance' },
    { title: 'Temporal analysis (Bi-LSTM)', detail: 'Inter-frame anomaly scoring' },
    { title: 'Audio synchronization (SyncNet)', detail: 'Cross-modal desync checks' },
    { title: 'Evidence generation & risk score', detail: 'Grad-CAM++ heatmap compilation' },
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 92) return prev;
        const next = prev + Math.floor(Math.random() * 8) + 4;
        const stepIndex = Math.min(steps.length - 1, Math.floor((next / 100) * steps.length));
        setCurrentStep(stepIndex);
        return next;
      });
    }, 450);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="forensic-card" style={{ maxWidth: '960px', margin: '0 auto', padding: '2rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.75rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffffff', letterSpacing: '-0.02em' }}>
            FORENSIC ANALYSIS IN PROGRESS
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Applying neural verification models to detect synthetic manipulation artifacts.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Loader2 size={16} className="animate-spin" color="var(--accent-blue)" />
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-blue)' }}>Processing</span>
        </div>
      </div>

      {/* Main Grid: Checklist + Frame Preview (Frame 4) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: '2rem',
          marginBottom: '2rem',
        }}
      >
        {/* Left Column: Audit Pipeline Checklist */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {steps.map((step, idx) => {
            const isDone = idx < currentStep;
            const isCurrent = idx === currentStep;
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.65rem 0.85rem',
                  borderRadius: '8px',
                  backgroundColor: isCurrent ? 'rgba(59, 130, 246, 0.1)' : 'var(--bg-dark)',
                  border: isCurrent ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid transparent',
                  transition: 'all 0.2s',
                }}
              >
                {isDone ? (
                  <CheckCircle2 size={18} color="var(--accent-green)" />
                ) : isCurrent ? (
                  <Loader2 size={18} className="animate-spin" color="var(--accent-blue)" />
                ) : (
                  <div style={{ width: '18px', height: '18px', borderRadius: '50%', border: '2px solid #334155' }} />
                )}

                <div>
                  <div
                    style={{
                      fontSize: '0.825rem',
                      fontWeight: isDone || isCurrent ? 600 : 500,
                      color: isDone ? '#ffffff' : isCurrent ? 'var(--accent-blue)' : 'var(--text-muted)',
                    }}
                  >
                    {step.title}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{step.detail}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: Active Frame Preview (Frame 4) */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: '280px',
              backgroundColor: '#070a12',
              borderRadius: '12px',
              overflow: 'hidden',
              border: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Simulated Face Image with Detection Overlay */}
            <img
              src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&auto=format&fit=crop&q=80"
              alt="Analyzing frame"
              style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.7 }}
            />

            {/* Bounding Box Overlay */}
            <div
              style={{
                position: 'absolute',
                width: '120px',
                height: '140px',
                border: '2px solid #ef4444',
                boxShadow: '0 0 12px rgba(239, 68, 68, 0.6)',
                borderRadius: '4px',
                top: '25%',
                left: '35%',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                padding: '4px',
              }}
            >
              <span style={{ fontSize: '9px', fontWeight: 800, color: '#ffffff', backgroundColor: '#ef4444', padding: '1px 4px', borderRadius: '2px' }}>
                FACE 01
              </span>
            </div>

            {/* Mini Player Bar Controls */}
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                padding: '0.5rem 1rem',
                backgroundColor: 'rgba(11, 15, 25, 0.85)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '0.75rem',
                color: '#ffffff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Play size={14} fill="#ffffff" />
                <span>01:10</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Volume2 size={14} />
                <Maximize2 size={14} />
              </div>
            </div>
          </div>
          <div style={{ marginTop: '0.5rem', fontSize: '0.725rem', color: 'var(--text-muted)', textAlign: 'center' }}>
            Live frame telemetry stream • ResNet-50 feature extraction active
          </div>
        </div>
      </div>

      {/* Bottom Overall Progress Bar (Frame 4) */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem' }}>
          <span style={{ color: 'var(--text-secondary)' }}>Overall Progress</span>
          <span style={{ color: 'var(--accent-blue)' }}>{progress}%</span>
        </div>
        <div style={{ width: '100%', height: '8px', backgroundColor: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
          <div
            style={{
              width: `${progress}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%)',
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      </div>
    </div>
  );
};
