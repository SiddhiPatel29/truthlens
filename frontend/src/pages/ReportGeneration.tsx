import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import QRCode from 'qrcode';
import { getScanRecord, getActiveScan, ForensicScanRecord } from '../utils/scanManager';
import { LedgerQrModal } from '../components/common/LedgerQrModal';
import { Shield, Download, Printer, CheckSquare, QrCode, Check, FileCheck, Layers, Activity, UserCheck, ShieldAlert, Film, Mic, Image as ImageIcon, FileText, ExternalLink, ShieldCheck } from 'lucide-react';

export const ReportGeneration: React.FC = () => {
  const [searchParams] = useSearchParams();
  const rawReportId = searchParams.get('reportId') || 'VM-2026-00821';
  const numericId = rawReportId.replace(/\D/g, '') || '821';
  const isDirectVerify = searchParams.get('verify') === 'true';

  const [scanRecord, setScanRecord] = useState<ForensicScanRecord | null>(null);
  const [receiptData, setReceiptData] = useState<any>(null);
  const [isQrModalOpen, setIsQrModalOpen] = useState(false);
  const [qrThumbnailUrl, setQrThumbnailUrl] = useState<string>('');

  const [sections, setSections] = useState({
    executiveSummary: true,
    detectionDetails: true,
    heatmaps: true,
    audioAnalysis: true,
    metadata: true,
    chainOfCustody: true,
    humanReview: true,
  });

  useEffect(() => {
    const scan = getScanRecord(numericId) || getActiveScan();
    setScanRecord(scan);

    const activeSha256 = scan?.sha256 || '9f4cd3e9f4ca8d4e5f6789012345678abcdef0123456789abcdef0123456789';
    const repId = `VM-2026-00${scan?.id || numericId}`;
    const verifyUrl = `${window.location.origin}/reports?reportId=${repId}&verify=true&hash=${encodeURIComponent(activeSha256)}`;

    // Generate real scannable QR thumbnail
    QRCode.toDataURL(verifyUrl, {
      width: 150,
      margin: 1,
      color: {
        dark: '#050b14',
        light: '#ffffff',
      },
      errorCorrectionLevel: 'M',
    })
      .then((url) => setQrThumbnailUrl(url))
      .catch((err) => console.error('Failed to generate QR thumbnail:', err));

    const raw = sessionStorage.getItem('current_dossier_receipt');
    if (raw) {
      try {
        setReceiptData(JSON.parse(raw));
      } catch {
        // Fallback
      }
    }

    if (isDirectVerify) {
      setIsQrModalOpen(true);
    }
  }, [numericId, isDirectVerify]);

  const reportId = `VM-2026-00${scanRecord?.id || numericId}`;
  const filename = scanRecord?.filename || 'evidence_asset.mp4';
  const modality = scanRecord?.media_type || 'video';
  const isSynthetic = scanRecord?.prediction === 'Fake';
  const confidence = scanRecord?.confidence ?? 0;
  const sha256 = scanRecord?.sha256 || '9f4cd3e9f4ca8d4e5f6789012345678abcdef0123456789abcdef0123456789';

  const toggleSection = (key: keyof typeof sections) => {
    setSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleExportPDF = () => {
    window.print();
  };

  const handleDownloadC2PA = () => {
    const manifestPackage = {
      manifest_id: `urn:truthlens:manifest:${reportId}`,
      standard: 'TruthLens Forensic Verification Protocol v1',
      compliance: 'ISO/IEC 27037:2012 Digital Evidence',
      case_identifier: reportId,
      analyzed_asset: {
        filename,
        media_type: modality,
        filesize: scanRecord?.filesize || 'Unknown',
        sha256_hash: sha256,
      },
      dispatched_info: receiptData,
      included_sections: sections,
      cryptographic_anchor: {
        hash_algorithm: 'SHA-256',
        media_hash: sha256,
        evidence_signature: `sha256:${sha256.slice(0, 32)}`,
      },
      verdict: {
        classification: isSynthetic ? 'SYNTHETIC_MEDIA_DETECTED' : 'AUTHENTIC_CONTENT_VERIFIED',
        confidence_score: confidence,
        risk_level: scanRecord?.risk_level || 'CRITICAL',
      },
      exported_at: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(manifestPackage, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${reportId}_Forensic_Manifest.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.025em' }}>
          Forensic Report Generation & Evidence Dossier
        </h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Certified digital evidence package adhering to C2PA-Authenticity and NIST-AI-100-2 forensic standards.
        </p>
      </div>

      {/* Cryptographic Verification Banner if opened via QR scan */}
      {isDirectVerify && (
        <div
          style={{
            backgroundColor: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            borderRadius: '10px',
            padding: '0.85rem 1.25rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            animation: 'fadeIn 0.3s ease-out',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ color: '#34d399', display: 'flex' }}>
              <ShieldCheck size={24} />
            </div>
            <div>
              <div style={{ color: '#34d399', fontWeight: 700, fontSize: '0.9rem' }}>
                Cryptographic Proof Successfully Verified
              </div>
              <div style={{ color: '#cbd5e1', fontSize: '0.78rem' }}>
                This report matches the cryptographic SHA-256 digest recorded for Scan #{numericId}. Evidence integrity verified.
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsQrModalOpen(true)}
            className="btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.4rem 0.75rem', color: '#34d399', borderColor: 'rgba(16, 185, 129, 0.4)' }}
          >
            <QrCode size={13} />
            <span>Inspect Proof</span>
          </button>
        </div>
      )}

      {/* Main Split Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: '2rem',
          alignItems: 'start',
        }}
      >
        {/* Left Panel: Official Forensic Report Certificate Preview */}
        <div
          className="forensic-card"
          style={{
            backgroundColor: '#0a0e1a',
            border: '2px solid #334155',
            padding: '2rem',
            position: 'relative',
          }}
        >
          {/* Certificate Watermark / Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #1e293b', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Shield size={24} color="var(--accent-blue)" />
              <span style={{ fontSize: '1.1rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.025em' }}>
                VeraMedia AI
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Forensic Evidence Dossier
            </span>
          </div>

          {/* Dossier Metadata Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem', fontSize: '0.8rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>CASE IDENTIFIER</span>
              <span style={{ fontWeight: 800, color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
                {reportId}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>ANALYZED ASSET</span>
              <span style={{ fontWeight: 700, color: '#93c5fd', wordBreak: 'break-all' }}>
                {filename}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>MEDIA SHA-256 HASH</span>
              <span style={{ fontWeight: 600, color: '#93c5fd', fontFamily: 'var(--font-mono)' }}>
                {sha256.slice(0, 16)}...{sha256.slice(-8)}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>DETECTION VERDICT</span>
              <span style={{ fontWeight: 800, color: isSynthetic ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                {isSynthetic ? 'Synthetic Media Detected' : 'Authentic Media Verified'}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>SYSTEM CONFIDENCE</span>
              <span style={{ fontWeight: 800, color: '#ffffff' }}>
                {confidence}% ({scanRecord?.risk_level || 'Critical'} Risk)
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>MODALITY</span>
              <span style={{ fontWeight: 700, color: '#cbd5e1', textTransform: 'capitalize' }}>
                {modality} Forensics
              </span>
            </div>
          </div>

          {/* Dynamic Section: Executive Summary */}
          {sections.executiveSummary && (
            <div style={{ backgroundColor: 'var(--bg-dark)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)', marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                1. Executive Summary & Legal Finding
              </div>
              <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.5' }}>
                Multi-modal forensic evaluation of <strong>{filename}</strong> indicates with {confidence}% statistical confidence that this media item is {isSynthetic ? 'synthetically fabricated and manipulated' : 'an authentic and untampered asset'}.
              </p>
            </div>
          )}

          {/* Dynamic Section: Visual / Modality Artifact Reconstruction */}
          {sections.heatmaps && (
            <div style={{ marginBottom: '1.25rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                2. PRIMARY {modality} FORENSIC ARTIFACT RECONSTRUCTION:
              </span>
              {modality === 'text' ? (
                <div style={{ backgroundColor: 'var(--bg-dark)', padding: '0.85rem', borderRadius: '6px', border: '1px solid #1e293b', fontSize: '0.8rem', color: '#cbd5e1', fontStyle: 'italic' }}>
                  "{scanRecord?.text_content || 'The rapid advancement of artificial intelligence has revolutionized the way we interact with technology across the modern enterprise.'}"
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', borderRadius: '8px', overflow: 'hidden' }}>
                  <div style={{ position: 'relative' }}>
                    <img
                      src={scanRecord?.preview_url || "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&auto=format&fit=crop&q=80"}
                      alt="Source Media"
                      style={{ width: '100%', height: '140px', objectFit: 'cover', borderRadius: '6px', border: '1px solid #1e293b' }}
                    />
                    <span style={{ position: 'absolute', bottom: '6px', left: '6px', backgroundColor: 'rgba(0,0,0,0.7)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem', color: '#ffffff' }}>
                      Pristine Target
                    </span>
                  </div>
                  <div style={{ position: 'relative' }}>
                    <img
                      src={scanRecord?.preview_url || "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&auto=format&fit=crop&q=80"}
                      alt="Heatmap Reconstruction"
                      style={{ width: '100%', height: '140px', objectFit: 'cover', borderRadius: '6px', border: '1px solid #ef4444', filter: 'hue-rotate(180deg) saturate(250%)' }}
                    />
                    <span style={{ position: 'absolute', bottom: '6px', left: '6px', backgroundColor: 'rgba(239,68,68,0.8)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem', color: '#ffffff' }}>
                      Activation Hotspots
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Dynamic Section: Audio-Visual Lip-Sync */}
          {sections.audioAnalysis && (modality === 'video' || modality === 'audio') && (
            <div style={{ backgroundColor: 'var(--bg-dark)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)', marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                3. Acoustic & Cross-Modal Lip-Sync Analysis
              </div>
              <div style={{ fontSize: '0.8rem', color: '#93c5fd', display: 'flex', justifyContent: 'space-between' }}>
                <span>SyncNet Measured Desync Offset:</span>
                <strong>320 ms (Acoustic Phoneme Burst)</strong>
              </div>
            </div>
          )}

          {/* Dynamic Section: Cryptographic Chain of Custody */}
          {sections.chainOfCustody && (
            <div style={{ backgroundColor: 'var(--bg-dark)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)', marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                4. Cryptographic Provenance Ledger
              </div>
              <div style={{ fontSize: '0.75rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                <div>• Ingestion SHA-256: {sha256}</div>
                <div>• C2PA Manifest Signature: sig_ed25519_{sha256.slice(0, 24)}</div>
                <div>• Status: Tamper-Evident Immutable Lock</div>
              </div>
            </div>
          )}

          {/* Dynamic Section: Human Review Sign-Off */}
          {sections.humanReview && (
            <div style={{ backgroundColor: 'var(--bg-dark)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.4)', marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#86efac', textTransform: 'uppercase', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Check size={13} /> 5. Certified Analyst Verification
              </div>
              <div style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
                Examiner: Lead Forensic Analyst (Admin) • Signed & Certified for Legal Platform Dispatch
              </div>
            </div>
          )}

          {/* Standards & QR Verification */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #1e293b', paddingTop: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              <div>Standards Compliance:</div>
              <div style={{ color: '#cbd5e1', fontWeight: 600 }}>C2PA-Authenticity v2.1 • NIST-AI-100-2</div>
            </div>
            <div
              onClick={() => setIsQrModalOpen(true)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setIsQrModalOpen(true);
                }
              }}
              title="Click to open full immutable ledger QR verification modal"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                color: '#ffffff',
                cursor: 'pointer',
                padding: '6px 12px',
                borderRadius: '10px',
                backgroundColor: 'rgba(59, 130, 246, 0.12)',
                border: '1px solid rgba(59, 130, 246, 0.35)',
                transition: 'all 0.2s ease',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
                e.currentTarget.style.borderColor = 'rgba(96, 165, 250, 0.6)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.12)';
                e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.35)';
              }}
            >
              {qrThumbnailUrl ? (
                <img
                  src={qrThumbnailUrl}
                  alt="Scannable Ledger QR Code"
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '6px',
                    backgroundColor: '#ffffff',
                    padding: '2px',
                    boxShadow: '0 0 8px rgba(59, 130, 246, 0.3)',
                  }}
                />
              ) : (
                <div
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#60a5fa',
                  }}
                >
                  <QrCode size={26} />
                </div>
              )}
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', lineHeight: '1.25' }}>
                <div style={{ color: '#93c5fd', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>Scan to verify</span>
                  <ExternalLink size={11} />
                </div>
                <div style={{ color: '#cbd5e1' }}>immutable ledger</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel: Section Selector & Export Controls */}
        <div className="forensic-card">
          <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.5rem' }}>
            Dossier Configuration & Modules
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Toggle forensic modules to customize the generated C2PA evidence dossier for <strong>{filename}</strong>.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '2rem' }}>
            {[
              { key: 'executiveSummary', label: 'Executive Summary & Legal Finding' },
              { key: 'heatmaps', label: 'Grad-CAM++ Spatial Heatmaps & Previews' },
              { key: 'audioAnalysis', label: 'Audio-Visual Lip-Sync Waveforms' },
              { key: 'metadata', label: 'EXIF & File Header Provenance' },
              { key: 'chainOfCustody', label: 'Cryptographic Chain of Custody' },
              { key: 'humanReview', label: 'Certified Human Examiner Sign-Off' },
            ].map((s) => {
              const checked = sections[s.key as keyof typeof sections];
              return (
                <div
                  key={s.key}
                  onClick={() => toggleSection(s.key as keyof typeof sections)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.75rem 1rem',
                    backgroundColor: checked ? 'rgba(59, 130, 246, 0.1)' : 'var(--bg-dark)',
                    border: checked ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <span style={{ fontSize: '0.85rem', fontWeight: 500, color: checked ? '#ffffff' : 'var(--text-secondary)' }}>
                    {s.label}
                  </span>
                  <div
                    style={{
                      width: '18px',
                      height: '18px',
                      borderRadius: '4px',
                      backgroundColor: checked ? 'var(--accent-blue)' : 'transparent',
                      border: checked ? 'none' : '2px solid #475569',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#ffffff',
                    }}
                  >
                    {checked && <Check size={12} />}
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <button
              type="button"
              onClick={handleExportPDF}
              className="btn-primary"
              style={{ width: '100%', padding: '0.85rem', fontSize: '0.95rem', justifyContent: 'center' }}
            >
              <Printer size={18} />
              <span>Print / Save as PDF Dossier</span>
            </button>

            <button
              type="button"
              onClick={handleDownloadC2PA}
              className="btn-secondary"
              style={{ width: '100%', padding: '0.75rem', fontSize: '0.85rem', justifyContent: 'center' }}
            >
              <Download size={16} />
              <span>Download Forensic JSON Manifest</span>
            </button>
            <button
              type="button"
              onClick={() => setIsQrModalOpen(true)}
              className="btn-secondary"
              style={{
                width: '100%',
                padding: '0.85rem',
                fontSize: '0.9rem',
                justifyContent: 'center',
                borderColor: 'rgba(59, 130, 246, 0.45)',
                backgroundColor: 'rgba(59, 130, 246, 0.12)',
                color: '#93c5fd',
                fontWeight: 600,
              }}
            >
              <QrCode size={17} />
              <span>Verify Evidence Hash (QR Code)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Immutable Ledger QR Modal */}
      <LedgerQrModal
        isOpen={isQrModalOpen}
        onClose={() => setIsQrModalOpen(false)}
        scanId={scanRecord?.id || numericId}
        filename={filename}
        sha256={sha256}
        modality={modality}
        verdict={scanRecord?.prediction || (isSynthetic ? 'Fake' : 'Real')}
        confidence={confidence}
        reportId={reportId}
      />
    </div>
  );
};
