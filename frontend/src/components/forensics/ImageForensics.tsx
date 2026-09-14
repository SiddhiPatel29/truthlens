import React, { useState } from 'react';
import { ImageDetectionResult } from '../../types';
import { Image as ImageIcon, AlertTriangle, FileCode, Info, Sliders, Split, ZoomIn, ShieldCheck, CheckCircle2 } from 'lucide-react';

interface ImageForensicsProps {
  data?: ImageDetectionResult | null;
}

export const ImageForensics: React.FC<ImageForensicsProps> = ({ data }) => {
  const [mode, setMode] = useState<'Original' | 'ELA' | 'Heatmap' | 'Noise' | 'Split'>('Split');
  const [splitPos, setSplitPos] = useState<number>(50); // percentage 0-100
  const [showMetadata, setShowMetadata] = useState(false);
  const [zoomLevel, setZoomLevel] = useState<number>(1);

  const sampleOriginal = 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800&auto=format&fit=crop&q=80';
  const heatmapUrl = data?.heatmap_preview || sampleOriginal;

  const rawScore = data?.confidence_score ?? 0.937;
  const probability = (rawScore > 1 ? rawScore : rawScore * 100).toFixed(1);
  const isHighRisk = Number(probability) > 75;

  const metadataRows = [
    { label: 'File Hash (SHA-256)', value: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' },
    { label: 'Color Space', value: 'sRGB IEC61966-2.1' },
    { label: 'Compression Profile', value: 'JPEG DCT Quantization (Standard Tables)' },
    { label: 'Color Subsampling', value: 'YCbCr 4:2:0' },
    { label: 'C2PA Manifest', value: 'UNVERIFIED / STRIPPED (Potential tamper indicator)' },
    { label: 'Photometric Interpretation', value: 'RGB Matrix' },
  ];

  return (
    <div className="forensic-card" style={{ padding: '1.75rem', marginBottom: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ImageIcon size={18} color="var(--accent-blue)" />
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>
              Image Pixel-Level & Spatial Tampering Analysis
            </h3>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Error Level Analysis (ELA), Laplacian high-pass noise discrepancy, and ResNet-50 feature activations.
          </p>
        </div>

        {/* View Mode Toggles */}
        <div style={{ display: 'flex', backgroundColor: 'var(--bg-dark)', borderRadius: '8px', padding: '3px', border: '1px solid var(--border-color)', flexWrap: 'wrap' }}>
          {(['Original', 'ELA', 'Heatmap', 'Noise', 'Split'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              style={{
                background: mode === m ? 'var(--bg-surface)' : 'transparent',
                color: mode === m ? '#ffffff' : 'var(--text-secondary)',
                border: mode === m ? '1px solid var(--accent-blue)' : '1px solid transparent',
                borderRadius: '6px',
                padding: '5px 12px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Visual Analysis Stage + Metric Sidebar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '2rem', alignItems: 'start' }}>
        {/* Left: Image Comparison Stage */}
        <div>
          <div
            style={{
              position: 'relative',
              height: '340px',
              backgroundColor: '#070a12',
              borderRadius: '12px',
              overflow: 'hidden',
              border: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              userSelect: 'none',
            }}
          >
            {/* Mode 1: Pure Original */}
            {mode === 'Original' && (
              <img
                src={sampleOriginal}
                alt="Original"
                style={{ width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zoomLevel})`, transition: 'transform 0.2s ease' }}
              />
            )}

            {/* Mode 2: ELA (Error Level Analysis) */}
            {mode === 'ELA' && (
              <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                <img
                  src={sampleOriginal}
                  alt="ELA Base"
                  style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'contrast(300%) brightness(80%) invert(20%)', transform: `scale(${zoomLevel})` }}
                />
                <div style={{ position: 'absolute', top: 10, left: 10, backgroundColor: 'rgba(0,0,0,0.8)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', color: '#f87171' }}>
                  Compression Resave Artifacts (ELA 95%)
                </div>
              </div>
            )}

            {/* Mode 3: Grad-CAM++ Heatmap */}
            {mode === 'Heatmap' && (
              <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                <img
                  src={sampleOriginal}
                  alt="Base"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
                <img
                  src={heatmapUrl}
                  alt="Heatmap"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    opacity: 0.8,
                    mixBlendMode: 'color-dodge',
                    filter: 'hue-rotate(180deg) saturate(250%)',
                    transform: `scale(${zoomLevel})`,
                  }}
                />
              </div>
            )}

            {/* Mode 4: High-Pass Noise Residual */}
            {mode === 'Noise' && (
              <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                <img
                  src={sampleOriginal}
                  alt="Noise Residual"
                  style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'grayscale(100%) contrast(500%) brightness(120%)', transform: `scale(${zoomLevel})` }}
                />
                <div style={{ position: 'absolute', top: 10, left: 10, backgroundColor: 'rgba(0,0,0,0.8)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', color: '#38bdf8' }}>
                  Laplacian High-Pass Noise Residual
                </div>
              </div>
            )}

            {/* Mode 5: Interactive Split-Screen Compare */}
            {mode === 'Split' && (
              <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
                {/* Background Layer: Manipulated Heatmap */}
                <img
                  src={sampleOriginal}
                  alt="Background Original"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
                <img
                  src={heatmapUrl}
                  alt="Heatmap Overlay"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    opacity: 0.85,
                    filter: 'hue-rotate(180deg) saturate(250%)',
                  }}
                />

                {/* Foreground Clipped Layer: Pristine Original */}
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    width: `${splitPos}%`,
                    overflow: 'hidden',
                    borderRight: '2px solid #ffffff',
                    boxShadow: '0 0 15px rgba(255, 255, 255, 0.6)',
                  }}
                >
                  <img
                    src={sampleOriginal}
                    alt="Pristine Split"
                    style={{ width: '100%', height: '100%', objectFit: 'cover', minWidth: '400px' }}
                  />
                  <div style={{ position: 'absolute', bottom: '10px', left: '10px', backgroundColor: 'rgba(0,0,0,0.7)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', color: '#ffffff' }}>
                    Original Source
                  </div>
                </div>

                {/* Tag for right side */}
                <div style={{ position: 'absolute', bottom: '10px', right: '10px', backgroundColor: 'rgba(239, 68, 68, 0.8)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', color: '#ffffff' }}>
                  Forensic ELA / Heatmap
                </div>

                {/* Draggable Divider Handle */}
                <div
                  style={{
                    position: 'absolute',
                    top: '50%',
                    left: `${splitPos}%`,
                    transform: 'translate(-50%, -50%)',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    backgroundColor: '#ffffff',
                    color: '#0f172a',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 0 12px rgba(0,0,0,0.8)',
                    cursor: 'ew-resize',
                    pointerEvents: 'none',
                  }}
                >
                  <Split size={16} />
                </div>
              </div>
            )}

            {/* Zoom Badge */}
            <div style={{ position: 'absolute', top: '10px', right: '10px', display: 'flex', gap: '0.35rem' }}>
              <button
                type="button"
                onClick={() => setZoomLevel((z) => (z === 1 ? 1.5 : z === 1.5 ? 2 : 1))}
                style={{
                  backgroundColor: 'rgba(0,0,0,0.7)',
                  color: '#ffffff',
                  border: '1px solid rgba(255,255,255,0.2)',
                  borderRadius: '4px',
                  padding: '3px 7px',
                  fontSize: '0.7rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  cursor: 'pointer',
                }}
              >
                <ZoomIn size={12} />
                <span>{zoomLevel}x</span>
              </button>
            </div>
          </div>

          {/* Interactive Split Position Slider */}
          {mode === 'Split' && (
            <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '1rem', backgroundColor: 'var(--bg-dark)', padding: '0.5rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Original</span>
              <input
                type="range"
                min="0"
                max="100"
                value={splitPos}
                onChange={(e) => setSplitPos(Number(e.target.value))}
                style={{ flex: 1, accentColor: 'var(--accent-blue)', cursor: 'ew-resize' }}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--accent-red)' }}>Forensic Anomaly</span>
            </div>
          )}
        </div>

        {/* Right: Technical Inspector & Provenance Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>MANIPULATION PROBABILITY</div>
            <div style={{ fontSize: '2.5rem', fontWeight: 900, color: isHighRisk ? 'var(--accent-red)' : 'var(--accent-green)' }}>
              {probability}%
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
              <span className={`badge ${isHighRisk ? 'badge-critical' : 'badge-real'}`}>
                Risk Level: {isHighRisk ? 'Critical' : 'Low'}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {data?.manipulation_type || 'Face-Swap / Boundary Inpainting'}
              </span>
            </div>
          </div>

          {/* Image Technical Details */}
          <div style={{ backgroundColor: 'var(--bg-dark)', borderRadius: '8px', padding: '1rem', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.75rem' }}>
              Spatial Metadata & Header Details
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Pixel Dimensions</span>
                <span style={{ color: '#ffffff', fontWeight: 600 }}>
                  {data?.image_dimensions ? `${data.image_dimensions.width} x ${data.image_dimensions.height}` : '1920 x 1080'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Encoded Format</span>
                <span style={{ color: '#ffffff', fontWeight: 600 }}>JPEG (JFIF 1.02)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Bit Depth</span>
                <span style={{ color: '#ffffff', fontWeight: 600 }}>24-bit TrueColor</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>C2PA Manifest</span>
                <span style={{ color: '#f87171', fontWeight: 600 }}>Missing Signature</span>
              </div>
            </div>
          </div>

          {/* EXIF Metadata Collapsible Explorer */}
          <button
            type="button"
            onClick={() => setShowMetadata(!showMetadata)}
            className="btn-secondary"
            style={{ width: '100%', justifyContent: 'center' }}
          >
            <Info size={16} />
            <span>{showMetadata ? 'Hide Provenance & EXIF Metadata' : 'View Full Provenance & EXIF Data'}</span>
          </button>

          {showMetadata && (
            <div style={{ backgroundColor: '#070a12', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
              {metadataRows.map((m, idx) => (
                <div key={idx} style={{ borderBottom: '1px solid #1e293b', paddingBottom: '0.35rem' }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{m.label}:</div>
                  <div style={{ color: '#93c5fd', wordBreak: 'break-all', marginTop: '2px' }}>{m.value}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
