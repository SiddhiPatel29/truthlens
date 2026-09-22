import React, { useState, useEffect } from 'react';
import { AudioDetectionResult, AudioLipSyncDiscrepancy } from '../../types';
import { Mic, AlertTriangle, Activity, Play, Pause, Sliders, Volume2, CheckCircle2, ShieldAlert } from 'lucide-react';

interface AudioLipSyncProps {
  data?: AudioDetectionResult | null;
}

export const AudioLipSync: React.FC<AudioLipSyncProps> = ({ data }) => {
  const [selectedDiscrepancy, setSelectedDiscrepancy] = useState<number | null>(0);
  const [toleranceMs, setToleranceMs] = useState<number>(150);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playheadPos, setPlayheadPos] = useState<number>(35); // percentage (0 - 100)
  const [showAudioWave, setShowAudioWave] = useState(true);
  const [showVisemeWave, setShowVisemeWave] = useState(true);

  const defaultDiscrepancies: AudioLipSyncDiscrepancy[] = [
    {
      start_timestamp: '00:12.4',
      end_timestamp: '00:15.8',
      measured_offset_ms: 320,
      severity: 'HIGH',
      description: 'Phoneme plosive burst desynchronized with visual viseme mouth closure (bilabial /b/ sound delay).',
    },
    {
      start_timestamp: '00:21.4',
      end_timestamp: '00:24.1',
      measured_offset_ms: 180,
      severity: 'MEDIUM',
      description: 'Formant F1/F2 frequency transition lag against mandibular opening trajectory.',
    },
    {
      start_timestamp: '00:36.0',
      end_timestamp: '00:38.5',
      measured_offset_ms: 95,
      severity: 'LOW',
      description: 'Micro-delay during alveolar fricative /s/ sound articulation.',
    },
  ];

  const discrepancies = data?.lip_sync_discrepancies?.length
    ? data.lip_sync_discrepancies
    : defaultDiscrepancies;

  // Audio playhead simulation loop
  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setPlayheadPos((prev) => (prev >= 100 ? 0 : prev + 2));
    }, 100);
    return () => clearInterval(timer);
  }, [isPlaying]);

  // Compute filtered discrepancies based on tolerance threshold
  const activeIssues = discrepancies.filter((d) => d.measured_offset_ms >= toleranceMs);

  // Dynamic sync score calculation based on tolerance and active discrepancies
  const baseConfidence = data?.confidence_score ?? 0.88;
  const syncScore = Math.max(30, Math.round(100 - (activeIssues.length * 14.5) - (baseConfidence * 20)));

  return (
    <div className="forensic-card" style={{ padding: '1.75rem', marginBottom: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Mic size={18} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>
              Audio Signal Analysis & Cross-Modal Consistency
            </h3>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Acoustic signal and cross-modal consistency analysis tracking spectral variance and temporal alignment indicators.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>CONSISTENCY SCORE</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 900, color: syncScore < 70 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
              {syncScore}%
            </div>
          </div>
          {activeIssues.length > 0 ? (
            <span className="badge badge-fake">
              <AlertTriangle size={12} /> {activeIssues.length} Discrepancy Points
            </span>
          ) : (
            <span className="badge badge-real">
              <CheckCircle2 size={12} /> Consistent
            </span>
          )}
        </div>
      </div>

      {/* Waveform Visualization Graphic with Playback Simulation */}
      <div style={{ backgroundColor: 'var(--bg-dark)', borderRadius: '10px', padding: '1.25rem', border: '1px solid var(--border-color)', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={() => setIsPlaying(!isPlaying)}
              className="btn-secondary"
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
            >
              {isPlaying ? <Pause size={13} /> : <Play size={13} />}
              <span>{isPlaying ? 'Pause Audio' : 'Play Audio Signal Track'}</span>
            </button>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {((playheadPos / 100) * 45).toFixed(1)}s / 45.0s
            </span>
          </div>

          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.725rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', color: showAudioWave ? '#38bdf8' : 'var(--text-muted)' }}>
              <input type="checkbox" checked={showAudioWave} onChange={(e) => setShowAudioWave(e.target.checked)} style={{ display: 'none' }} />
              <span>■ Acoustic Signal Wave</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', color: showVisemeWave ? '#f87171' : 'var(--text-muted)' }}>
              <input type="checkbox" checked={showVisemeWave} onChange={(e) => setShowVisemeWave(e.target.checked)} style={{ display: 'none' }} />
              <span>■ Cross-Modal Temporal Track</span>
            </label>
          </div>
        </div>

        {/* Dual Colored Audio Waves with Live Moving Playhead */}
        <div style={{ height: '110px', width: '100%', position: 'relative', overflow: 'hidden', borderRadius: '6px', backgroundColor: '#070a12' }}>
          <svg viewBox="0 0 600 100" preserveAspectRatio="none" style={{ width: '100%', height: '100%' }}>
            {/* Background Grid Lines */}
            <line x1="0" y1="50" x2="600" y2="50" stroke="#1e293b" strokeWidth="1" strokeDasharray="4 4" />
            <line x1="150" y1="0" x2="150" y2="100" stroke="#1e293b" strokeWidth="0.5" />
            <line x1="300" y1="0" x2="300" y2="100" stroke="#1e293b" strokeWidth="0.5" />
            <line x1="450" y1="0" x2="450" y2="100" stroke="#1e293b" strokeWidth="0.5" />

            {/* Audio Wave (Cyan) */}
            {showAudioWave && (
              <path
                d="M 0 50 Q 25 10, 50 50 T 100 80 T 150 20 T 200 70 T 250 15 T 300 85 T 350 25 T 400 75 T 450 30 T 500 70 T 550 40 T 600 50"
                fill="none"
                stroke="var(--accent-cyan)"
                strokeWidth="2"
                opacity="0.9"
              />
            )}

            {/* Viseme Wave (Red Anomaly Overlay) */}
            {showVisemeWave && (
              <path
                d="M 0 50 Q 25 25, 50 50 T 100 65 T 150 45 T 200 50 T 250 85 T 300 15 T 350 75 T 400 25 T 450 50 T 500 50 T 550 50 T 600 50"
                fill="none"
                stroke="var(--accent-red)"
                strokeWidth="2"
                opacity="0.85"
              />
            )}

            {/* Desync Zone Shading for Selected Discrepancy */}
            {selectedDiscrepancy !== null && (
              <rect
                x={selectedDiscrepancy === 0 ? '160' : selectedDiscrepancy === 1 ? '280' : '480'}
                y="10"
                width="60"
                height="80"
                fill="rgba(239, 68, 68, 0.2)"
                stroke="rgba(239, 68, 68, 0.6)"
                strokeDasharray="3 3"
              />
            )}

            {/* Live Animated Playhead */}
            <line
              x1={(playheadPos / 100) * 600}
              y1="0"
              x2={(playheadPos / 100) * 600}
              y2="100"
              stroke="#ffffff"
              strokeWidth="2"
            />
          </svg>
        </div>

        {/* Sync Timeline Track */}
        <div style={{ marginTop: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
            <span>Acoustic Signal & Temporal Track</span>
            <span>Offset Tolerance Filter: &gt; {toleranceMs}ms</span>
          </div>
          <div style={{ width: '100%', height: '10px', display: 'flex', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: '25%', backgroundColor: '#10b981' }} title="Consistent" />
            <div style={{ width: '15%', backgroundColor: '#ef4444' }} title="Discrepancy Event 1 (320ms)" />
            <div style={{ width: '20%', backgroundColor: '#10b981' }} title="Consistent" />
            <div style={{ width: '18%', backgroundColor: '#f59e0b' }} title="Discrepancy Event 2 (180ms)" />
            <div style={{ width: '22%', backgroundColor: '#10b981' }} title="Consistent" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            <span>00:00.0</span>
            <span>00:15.0</span>
            <span>00:30.0</span>
            <span>00:45.0</span>
          </div>
        </div>
      </div>

      {/* Dynamic Tolerance Threshold Filter Slider */}
      <div
        style={{
          backgroundColor: 'var(--bg-dark)',
          borderRadius: '8px',
          padding: '1rem',
          border: '1px solid var(--border-color)',
          marginBottom: '1.5rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <Sliders size={18} color="var(--accent-blue)" />
          <div>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#ffffff' }}>
              Cross-Modal Sensitivity Threshold: {toleranceMs} ms
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Ignore natural micro-latencies below this acoustic threshold.
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: '240px' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>50ms</span>
          <input
            type="range"
            min="50"
            max="400"
            step="10"
            value={toleranceMs}
            onChange={(e) => setToleranceMs(Number(e.target.value))}
            style={{ flex: 1, accentColor: 'var(--accent-blue)', cursor: 'pointer' }}
          />
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>400ms</span>
        </div>
      </div>

      {/* Desync Segments Table (Interactive Selection) */}
      <div>
        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
          DETECTED CROSS-MODAL DISCREPANCY EVENTS (CLICK TO INSPECT)
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {discrepancies.map((d, i) => {
            const isIgnored = d.measured_offset_ms < toleranceMs;
            const isSelected = selectedDiscrepancy === i;
            return (
              <div
                key={i}
                onClick={() => setSelectedDiscrepancy(i)}
                style={{
                  backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'var(--bg-dark)',
                  border: isSelected ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '0.85rem 1rem',
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '0.75rem',
                  cursor: 'pointer',
                  opacity: isIgnored ? 0.6 : 1,
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.825rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                    {d.start_timestamp} - {d.end_timestamp}
                  </span>
                  <span className={`badge ${d.severity === 'HIGH' ? 'badge-fake' : d.severity === 'MEDIUM' ? 'badge-uncertain' : 'badge-real'}`}>
                    {d.severity} ({d.measured_offset_ms}ms)
                  </span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {d.description}
                  </span>
                </div>

                {isIgnored && (
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    Below current threshold
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
