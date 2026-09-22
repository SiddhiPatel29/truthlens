import React, { useState, useEffect } from 'react';
import { VideoDetectionResult } from '../../types';
import { Play, Pause, SkipBack, SkipForward, CheckCircle2, AlertTriangle, Eye, Activity, Crosshair, Layers } from 'lucide-react';

interface VideoForensicsProps {
  data?: VideoDetectionResult | null;
}

export const VideoForensics: React.FC<VideoForensicsProps> = ({ data }) => {
  const [selectedFrame, setSelectedFrame] = useState(2);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showBoundingBox, setShowBoundingBox] = useState(true);
  const [showLandmarks, setShowLandmarks] = useState(true);
  const [showFlowVectors, setShowFlowVectors] = useState(false);

  const fallbackFrames = [
    { id: 0, frameNum: 42, time: '00:04.2', score: 92.4, jitter: '0.12mm', thumb: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&auto=format&fit=crop&q=80', status: 'Suspicious' },
    { id: 1, frameNum: 85, time: '00:08.5', score: 91.1, jitter: '0.15mm', thumb: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&auto=format&fit=crop&q=80', status: 'Suspicious' },
    { id: 2, frameNum: 121, time: '00:12.1', score: 95.8, jitter: '0.38mm', thumb: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&auto=format&fit=crop&q=80', status: 'Peak Anomaly' },
    { id: 3, frameNum: 159, time: '00:15.9', score: 94.2, jitter: '0.29mm', thumb: 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&auto=format&fit=crop&q=80', status: 'Suspicious' },
    { id: 4, frameNum: 184, time: '00:18.4', score: 97.3, jitter: '0.42mm', thumb: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&auto=format&fit=crop&q=80', status: 'Critical Anomaly' },
  ];

  const frames = fallbackFrames.map((f, i) => {
    if (i === 2 && data?.keyframe_heatmap_preview) {
      return { ...f, thumb: data.keyframe_heatmap_preview };
    }
    return f;
  });

  const active = frames[selectedFrame];

  // Auto-play timeline simulation
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setSelectedFrame((prev) => (prev + 1) % frames.length);
    }, 1200);
    return () => clearInterval(interval);
  }, [isPlaying, frames.length]);

  const temporalConsistencyScore = data?.metrics?.temporal_instability
    ? Math.max(10, Math.round(100 - (data.metrics.temporal_instability * 100)))
    : 72;

  // Normalized coordinates for graph (SVG 300 x 100)
  const graphPoints = [
    { x: 30, y: 70, id: 0 },
    { x: 90, y: 65, id: 1 },
    { x: 150, y: 25, id: 2 },
    { x: 210, y: 35, id: 3 },
    { x: 270, y: 18, id: 4 },
  ];

  return (
    <div className="forensic-card" style={{ padding: '1.75rem', marginBottom: '1.5rem' }}>
      {/* Header & Tracking Status */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={18} color="var(--accent-blue)" />
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>
              Video Temporal Frame & Consistency Forensics
            </h3>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Temporal frame consistency analysis tracking inter-frame stability, visual jitter, and artifact continuity.
          </p>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
          <span className="badge" style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
            Total Frames: {data?.metrics?.total_frames_analyzed || 300}
          </span>
          <span className="badge badge-fake">
            <AlertTriangle size={12} /> Landmark Jitter: Elevated
          </span>
          <span className="badge badge-real">
            <CheckCircle2 size={12} /> Tracking: Stable
          </span>
        </div>
      </div>

      {/* Main Grid: Temporal Graph + Keyframe Preview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.75rem', marginBottom: '1.5rem' }}>
        {/* Left: Temporal Analysis Graph */}
        <div style={{ backgroundColor: 'var(--bg-dark)', padding: '1.25rem', borderRadius: '10px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                TEMPORAL CONSISTENCY SCORE
              </span>
              <span style={{ fontSize: '1.35rem', fontWeight: 800, color: temporalConsistencyScore < 60 ? 'var(--accent-red)' : 'var(--accent-amber)' }}>
                {temporalConsistencyScore}%
              </span>
            </div>

            <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              Periodic inter-frame jitter detected between frame 120 and 185. Anomaly spikes correlate with facial warping.
            </div>

            {/* Interactive SVG Curve with Clickable Keyframe Nodes */}
            <div style={{ height: '140px', width: '100%', position: 'relative', margin: '0.5rem 0' }}>
              <svg viewBox="0 0 300 100" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
                <defs>
                  <linearGradient id="curveGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <path
                  d="M 0 50 Q 30 20, 60 50 T 120 75 T 180 20 T 240 65 T 300 40"
                  fill="none"
                  stroke="var(--accent-amber)"
                  strokeWidth="2.5"
                />
                <line x1="0" y1="50" x2="300" y2="50" stroke="#334155" strokeDasharray="4 4" />
                {/* Active Frame Vertical Playhead Line */}
                <line
                  x1={graphPoints[selectedFrame].x}
                  y1="10"
                  x2={graphPoints[selectedFrame].x}
                  y2="90"
                  stroke="var(--accent-cyan)"
                  strokeWidth="1.5"
                  strokeDasharray="2 2"
                />

                {/* Clickable Keyframe Nodes */}
                {graphPoints.map((pt) => {
                  const isSelected = selectedFrame === pt.id;
                  return (
                    <g key={pt.id} onClick={() => setSelectedFrame(pt.id)} style={{ cursor: 'pointer' }}>
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r={isSelected ? '6' : '4'}
                        fill={isSelected ? '#38bdf8' : '#ef4444'}
                        stroke="#ffffff"
                        strokeWidth={isSelected ? '2' : '1'}
                      />
                      {isSelected && (
                        <circle
                          cx={pt.x}
                          cy={pt.y}
                          r="12"
                          fill="none"
                          stroke="#38bdf8"
                          strokeWidth="1.5"
                          opacity="0.6"
                          className="animate-pulse"
                        />
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              <span>Frame 0 (00:00.0)</span>
              <span style={{ color: 'var(--accent-red)', fontWeight: 600 }}>Peak Anomaly (F184)</span>
              <span>Frame 300 (00:20.0)</span>
            </div>
          </div>

          {/* Interactive Playback Simulation Controls */}
          <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => setSelectedFrame((p) => (p - 1 + frames.length) % frames.length)}
                className="btn-secondary"
                style={{ padding: '5px 8px', fontSize: '0.75rem' }}
                title="Previous Frame"
              >
                <SkipBack size={13} />
              </button>
              <button
                type="button"
                onClick={() => setIsPlaying(!isPlaying)}
                className="btn-primary"
                style={{ padding: '5px 12px', fontSize: '0.75rem' }}
              >
                {isPlaying ? <Pause size={13} /> : <Play size={13} />}
                <span>{isPlaying ? 'Pause' : 'Play Timeline'}</span>
              </button>
              <button
                type="button"
                onClick={() => setSelectedFrame((p) => (p + 1) % frames.length)}
                className="btn-secondary"
                style={{ padding: '5px 8px', fontSize: '0.75rem' }}
                title="Next Frame"
              >
                <SkipForward size={13} />
              </button>
            </div>

            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
              Frame {active.frameNum} ({active.time})
            </div>
          </div>
        </div>

        {/* Center/Right: Video Keyframe with Interactive Bounding Overlays */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ position: 'relative', height: '240px', borderRadius: '10px', overflow: 'hidden', border: '1px solid #334155', backgroundColor: '#070a12' }}>
            <img
              src={active.thumb}
              alt="Selected Video Keyframe"
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />

            {/* Facial Landmark Tracking Box */}
            {showBoundingBox && (
              <div
                style={{
                  position: 'absolute',
                  top: '18%',
                  left: '32%',
                  width: '110px',
                  height: '130px',
                  border: '2px solid #ef4444',
                  borderRadius: '4px',
                  boxShadow: '0 0 12px rgba(239, 68, 68, 0.7)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  padding: '4px',
                  transition: 'all 0.2s ease',
                }}
              >
                <span style={{ backgroundColor: '#ef4444', color: 'white', fontSize: '8px', fontWeight: 800, padding: '1px 4px', borderRadius: '2px' }}>
                  ANOMALY {active.score}%
                </span>
              </div>
            )}

            {/* 68-point Simulated Facial Landmark Dots */}
            {showLandmarks && (
              <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
                <circle cx="45%" cy="30%" r="2" fill="#22d3ee" />
                <circle cx="55%" cy="30%" r="2" fill="#22d3ee" />
                <circle cx="50%" cy="36%" r="2" fill="#22d3ee" />
                <circle cx="46%" cy="44%" r="2" fill="#ef4444" />
                <circle cx="50%" cy="45%" r="2" fill="#ef4444" />
                <circle cx="54%" cy="44%" r="2" fill="#ef4444" />
                <ellipse cx="50%" cy="35%" rx="28" ry="36" fill="none" stroke="#22d3ee" strokeDasharray="2 3" strokeWidth="1" opacity="0.6" />
              </svg>
            )}

            {/* Optical Flow Vector simulation */}
            {showFlowVectors && (
              <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 50% 40%, rgba(239,68,68,0.3) 0%, transparent 70%)', pointerEvents: 'none' }} />
            )}

            {/* Bottom time & status HUD */}
            <div
              style={{
                position: 'absolute',
                bottom: '8px',
                left: '12px',
                right: '12px',
                display: 'flex',
                justifyContent: 'space-between',
                backgroundColor: 'rgba(0,0,0,0.75)',
                padding: '3px 10px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                color: '#ffffff',
                backdropFilter: 'blur(4px)',
              }}
            >
              <span>Timestamp: {active.time}</span>
              <span style={{ color: active.score > 94 ? '#f87171' : '#fde047', fontWeight: 600 }}>{active.status}</span>
            </div>
          </div>

          {/* Overlay Toggles Bar */}
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => setShowBoundingBox(!showBoundingBox)}
              style={{
                backgroundColor: showBoundingBox ? 'rgba(239, 68, 68, 0.15)' : 'var(--bg-dark)',
                color: showBoundingBox ? '#fca5a5' : 'var(--text-muted)',
                border: showBoundingBox ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid var(--border-color)',
                padding: '4px 8px',
                borderRadius: '6px',
                fontSize: '0.725rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Crosshair size={12} />
              <span>Bounding Box</span>
            </button>
            <button
              type="button"
              onClick={() => setShowLandmarks(!showLandmarks)}
              style={{
                backgroundColor: showLandmarks ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-dark)',
                color: showLandmarks ? '#67e8f9' : 'var(--text-muted)',
                border: showLandmarks ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid var(--border-color)',
                padding: '4px 8px',
                borderRadius: '6px',
                fontSize: '0.725rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Eye size={12} />
              <span>Landmark Mesh</span>
            </button>
            <button
              type="button"
              onClick={() => setShowFlowVectors(!showFlowVectors)}
              style={{
                backgroundColor: showFlowVectors ? 'rgba(245, 158, 11, 0.15)' : 'var(--bg-dark)',
                color: showFlowVectors ? '#fde68a' : 'var(--text-muted)',
                border: showFlowVectors ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid var(--border-color)',
                padding: '4px 8px',
                borderRadius: '6px',
                fontSize: '0.725rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Layers size={12} />
              <span>Optical Flow</span>
            </button>
          </div>
        </div>
      </div>

      {/* Bottom: Suspicious Frames Carousel */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            EXTRACTED HIGH-ANOMALY KEYFRAMES (CLICK TO INSPECT)
          </div>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Active: Frame {active.frameNum} ({active.jitter} jitter)
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
          {frames.map((f) => (
            <div
              key={f.id}
              onClick={() => setSelectedFrame(f.id)}
              style={{
                backgroundColor: 'var(--bg-dark)',
                border: selectedFrame === f.id ? '2px solid var(--accent-red)' : '1px solid var(--border-color)',
                boxShadow: selectedFrame === f.id ? '0 0 12px rgba(239, 68, 68, 0.4)' : 'none',
                borderRadius: '8px',
                overflow: 'hidden',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                transform: selectedFrame === f.id ? 'scale(1.02)' : 'scale(1)',
              }}
            >
              <div style={{ position: 'relative' }}>
                <img src={f.thumb} alt={f.time} style={{ width: '100%', height: '80px', objectFit: 'cover' }} />
                <span
                  style={{
                    position: 'absolute',
                    top: '4px',
                    left: '4px',
                    backgroundColor: 'rgba(0,0,0,0.7)',
                    padding: '1px 5px',
                    borderRadius: '3px',
                    fontSize: '0.65rem',
                    color: '#ffffff',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  F{f.frameNum}
                </span>
              </div>
              <div style={{ padding: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{f.time}</span>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-red)' }}>{f.score}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
