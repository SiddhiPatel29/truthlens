import React, { useState, useEffect } from 'react';
import { Eye, Layers, Sliders, Play, Pause, ZoomIn, ZoomOut, RotateCcw, Crosshair } from 'lucide-react';

interface HeatmapViewerProps {
  heatmapUrl?: string | null;
  originalUrl?: string;
}

export const HeatmapViewer: React.FC<HeatmapViewerProps> = ({
  heatmapUrl,
  originalUrl = 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&auto=format&fit=crop&q=80',
}) => {
  const [viewMode, setViewMode] = useState<'Side-by-Side' | 'Overlay' | 'Original' | 'Heatmap' | 'Depth'>('Side-by-Side');
  const [intensity, setIntensity] = useState<number>(75);
  const [currentFrame, setCurrentFrame] = useState<number>(120);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [zoom, setZoom] = useState<number>(1);
  const [showBoundingBox, setShowBoundingBox] = useState<boolean>(true);
  const [showGradients, setShowGradients] = useState<boolean>(true);

  // Fallback simulated heatmap if not returned from backend
  const displayHeatmap =
    heatmapUrl ||
    'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&auto=format&fit=crop&q=80';

  // Automated playback loop
  useEffect(() => {
    let interval: any;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentFrame((prev) => (prev >= 300 ? 0 : prev + 4));
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isPlaying]);

  const formatTimestamp = (frame: number) => {
    const totalSeconds = frame / 30;
    const mins = Math.floor(totalSeconds / 60);
    const secs = (totalSeconds % 60).toFixed(2);
    return `${mins.toString().padStart(2, '0')}:${secs.padStart(5, '0')}`;
  };

  return (
    <div className="forensic-card" style={{ padding: '1.75rem', marginBottom: '1.5rem' }}>
      {/* Header & View Mode Switcher (Frame 6) */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          marginBottom: '1.25rem',
          borderBottom: '1px solid #1e293b',
          paddingBottom: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>
              Forensic Anomaly Heatmap Viewer
            </h3>
            <span className="badge badge-critical" style={{ fontSize: '0.65rem' }}>
              Artifact Anomaly Peak: {(intensity * 0.96).toFixed(1)}%
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Pixel-level forensic anomaly localization highlighting visual artifact boundaries and blending seams.
          </p>
        </div>

        {/* View Mode Tabs */}
        <div style={{ display: 'flex', backgroundColor: 'var(--bg-dark)', borderRadius: '8px', padding: '3px', border: '1px solid var(--border-color)' }}>
          {(['Side-by-Side', 'Overlay', 'Original', 'Heatmap', 'Depth'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              style={{
                background: viewMode === mode ? 'var(--accent-blue)' : 'transparent',
                color: viewMode === mode ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                borderRadius: '6px',
                padding: '5px 12px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Layer Toggles & Zoom Controls */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1rem',
          marginBottom: '1rem',
          fontSize: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showBoundingBox}
              onChange={(e) => setShowBoundingBox(e.target.checked)}
              style={{ accentColor: 'var(--accent-blue)' }}
            />
            <span>Facial Bounding Box</span>
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={showGradients}
              onChange={(e) => setShowGradients(e.target.checked)}
              style={{ accentColor: 'var(--accent-red)' }}
            />
            <span>Gradient Vectors</span>
          </label>
        </div>

        {/* Zoom Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <button
            onClick={() => setZoom((z) => Math.max(0.75, z - 0.25))}
            className="btn-secondary"
            style={{ padding: '3px 8px', fontSize: '0.7rem' }}
            title="Zoom Out"
          >
            <ZoomOut size={12} />
          </button>
          <span style={{ fontFamily: 'var(--font-mono)', minWidth: '40px', textAlign: 'center', color: '#93c5fd' }}>
            {(zoom * 100).toFixed(0)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(2.5, z + 0.25))}
            className="btn-secondary"
            style={{ padding: '3px 8px', fontSize: '0.7rem' }}
            title="Zoom In"
          >
            <ZoomIn size={12} />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="btn-secondary"
            style={{ padding: '3px 8px', fontSize: '0.7rem' }}
            title="Reset Zoom"
          >
            <RotateCcw size={12} />
          </button>
        </div>
      </div>

      {/* Main Display Stage (Frame 6) */}
      <div
        style={{
          minHeight: '380px',
          backgroundColor: '#070a12',
          borderRadius: '12px',
          overflow: 'hidden',
          border: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem',
          marginBottom: '1.5rem',
          position: 'relative',
        }}
      >
        <div style={{ transform: `scale(${zoom})`, transition: 'transform 0.2s ease', width: '100%', display: 'flex', justifyContent: 'center' }}>
          {viewMode === 'Side-by-Side' ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', width: '100%', maxWidth: '820px' }}>
              {/* Original Frame */}
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: 600 }}>
                  ORIGINAL FRAME ({formatTimestamp(currentFrame)})
                </div>
                <div style={{ position: 'relative', borderRadius: '10px', overflow: 'hidden', border: '1px solid #334155' }}>
                  <img src={originalUrl} alt="Original" style={{ width: '100%', height: '280px', objectFit: 'cover' }} />
                  <span style={{ position: 'absolute', bottom: '8px', left: '8px', background: 'rgba(0,0,0,0.7)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem' }}>
                    Frame #{currentFrame}
                  </span>
                </div>
              </div>

              {/* Heatmap Frame */}
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--accent-red)', marginBottom: '0.5rem', fontWeight: 600 }}>
                  FORENSIC ANOMALY HEATMAP ({intensity}% INTENSITY)
                </div>
                <div style={{ position: 'relative', borderRadius: '10px', overflow: 'hidden', border: '1px solid var(--accent-red)' }}>
                  <img
                    src={displayHeatmap}
                    alt="Heatmap"
                    style={{
                      width: '100%',
                      height: '280px',
                      objectFit: 'cover',
                      filter: `hue-rotate(180deg) saturate(${intensity * 2}%) contrast(${100 + intensity * 0.4}%)`,
                    }}
                  />

                  {/* Dynamic Bounding Box Overlay */}
                  {showBoundingBox && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '20%',
                        left: '28%',
                        width: '45%',
                        height: '55%',
                        border: '2px solid rgba(239, 68, 68, 0.9)',
                        borderRadius: '4px',
                        boxShadow: '0 0 14px rgba(239, 68, 68, 0.7)',
                        pointerEvents: 'none',
                      }}
                    >
                      <span style={{ position: 'absolute', top: '-18px', left: 0, backgroundColor: '#ef4444', color: 'white', fontSize: '9px', fontWeight: 800, padding: '1px 5px', borderRadius: '2px' }}>
                        MANIPULATION ZONE 94.8%
                      </span>
                    </div>
                  )}

                  {/* Gradient Vectors Indicator */}
                  {showGradients && (
                    <div style={{ position: 'absolute', top: '10px', right: '10px', background: 'rgba(0,0,0,0.75)', padding: '3px 8px', borderRadius: '4px', fontSize: '0.65rem', color: '#67e8f9', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Crosshair size={12} /> Vectors Active
                    </div>
                  )}

                  <span style={{ position: 'absolute', bottom: '8px', right: '8px', background: 'rgba(239,68,68,0.85)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 700 }}>
                    Boundary Discontinuity
                  </span>
                </div>
              </div>
            </div>
          ) : viewMode === 'Overlay' ? (
            <div style={{ position: 'relative', width: '100%', maxWidth: '480px', height: '320px', borderRadius: '10px', overflow: 'hidden', border: '1px solid #334155' }}>
              <img src={originalUrl} alt="Base" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
              <img
                src={displayHeatmap}
                alt="Heatmap Overlay"
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  opacity: intensity / 100,
                  mixBlendMode: 'color',
                  filter: `hue-rotate(180deg) saturate(${intensity * 2}%)`,
                }}
              />
              {showBoundingBox && (
                <div
                  style={{
                    position: 'absolute',
                    top: '22%',
                    left: '30%',
                    width: '42%',
                    height: '52%',
                    border: '2px solid rgba(239, 68, 68, 0.9)',
                    boxShadow: '0 0 12px rgba(239, 68, 68, 0.6)',
                  }}
                />
              )}
            </div>
          ) : (
            <div style={{ width: '100%', maxWidth: '480px', height: '320px', borderRadius: '10px', overflow: 'hidden', border: '1px solid #334155', position: 'relative' }}>
              <img
                src={viewMode === 'Original' ? originalUrl : displayHeatmap}
                alt="Selected View"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  filter:
                    viewMode === 'Depth'
                      ? 'grayscale(100%) contrast(160%)'
                      : viewMode === 'Heatmap'
                      ? `hue-rotate(180deg) saturate(${intensity * 2}%)`
                      : 'none',
                }}
              />
              <span style={{ position: 'absolute', bottom: '8px', left: '8px', background: 'rgba(0,0,0,0.7)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem' }}>
                Mode: {viewMode} • Frame #{currentFrame}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Scrubber & Intensity Slider Controls (Frame 6) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '2rem', alignItems: 'center' }}>
        {/* Timeline Scrubber with Play / Pause */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                style={{
                  background: isPlaying ? 'var(--accent-red)' : 'var(--accent-blue)',
                  border: 'none',
                  borderRadius: '4px',
                  color: 'white',
                  padding: '2px 6px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                }}
                title={isPlaying ? 'Pause Playback' : 'Play Timeline'}
              >
                {isPlaying ? <Pause size={12} /> : <Play size={12} />}
              </button>
              <span>Frame Scrubber</span>
            </div>
            <span style={{ fontWeight: 700, color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>
              Frame {currentFrame} ({formatTimestamp(currentFrame)})
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={300}
            value={currentFrame}
            onChange={(e) => setCurrentFrame(Number(e.target.value))}
          />
        </div>

        {/* Heatmap Intensity Slider */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
            <span>Heatmap Alpha Blending</span>
            <span style={{ fontWeight: 700, color: 'var(--accent-red)' }}>{intensity}%</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Low</span>
            <input
              type="range"
              min={10}
              max={100}
              value={intensity}
              onChange={(e) => setIntensity(Number(e.target.value))}
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>High</span>
          </div>
        </div>
      </div>
    </div>
  );
};
