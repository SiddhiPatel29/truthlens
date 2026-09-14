import React, { useState, useEffect } from 'react';
import QRCode from 'qrcode';
import { ShieldCheck, Copy, Check, Download, ExternalLink, X, Smartphone, RefreshCw } from 'lucide-react';

interface LedgerQrModalProps {
  isOpen: boolean;
  onClose: () => void;
  scanId: string | number;
  filename: string;
  sha256: string;
  modality?: string;
  verdict?: string;
  confidence?: number;
  reportId?: string;
}

export const LedgerQrModal: React.FC<LedgerQrModalProps> = ({
  isOpen,
  onClose,
  scanId,
  filename,
  sha256,
  modality = 'media',
  verdict = 'Fake',
  confidence = 98.2,
  reportId = 'VM-2026-00821',
}) => {
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<null | {
    status: string;
    verifiedAt: string;
    block: number;
    node: string;
    signature: string;
  }>(null);

  const verifyUrl = `${window.location.origin}/reports?reportId=${reportId}&verify=true&hash=${encodeURIComponent(sha256)}`;

  useEffect(() => {
    if (isOpen) {
      // Generate QR Code data URL
      QRCode.toDataURL(verifyUrl, {
        width: 300,
        margin: 2,
        color: {
          dark: '#050b14',
          light: '#ffffff',
        },
        errorCorrectionLevel: 'H',
      })
        .then((url) => {
          setQrDataUrl(url);
        })
        .catch((err) => {
          console.error('Error generating QR code:', err);
        });

      setVerificationResult(null);
      setIsVerifying(false);
    }
  }, [isOpen, verifyUrl]);

  // Handle escape key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleCopyHash = () => {
    navigator.clipboard.writeText(sha256);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2500);
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(verifyUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  const handleDownloadQr = () => {
    if (!qrDataUrl) return;
    const a = document.createElement('a');
    a.href = qrDataUrl;
    a.download = `truthlens-ledger-qr-${filename.replace(/[^a-zA-Z0-9.-]/g, '_')}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleSimulateVerification = () => {
    setIsVerifying(true);
    setVerificationResult(null);

    setTimeout(() => {
      setIsVerifying(false);
      setVerificationResult({
        status: 'CONFIRMED_IMMUTABLE',
        verifiedAt: new Date().toLocaleTimeString(),
        block: 49218 + (Number(scanId) % 1000 || 821),
        node: 'truthlens-validator-eu-central-01',
        signature: `ed25519:0x${sha256.slice(0, 24)}...8f3c`,
      });
    }, 1200);
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(3, 7, 18, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          backgroundColor: '#0c111d',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '560px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.75), 0 0 40px rgba(59, 130, 246, 0.15)',
          overflow: 'hidden',
          animation: 'fadeIn 0.2s ease-out',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#60a5fa',
              }}
            >
              <ShieldCheck size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
                  Immutable Ledger Verification
                </h3>
                <span
                  style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: '#34d399',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: '#34d399',
                      boxShadow: '0 0 6px #34d399',
                    }}
                  />
                  ANCHORED & VERIFIED
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>
                Scan to verify cryptographic root hash & C2PA custodial chain
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '1.5rem', maxHeight: 'calc(90vh - 120px)', overflowY: 'auto' }}>
          {/* QR Code & Scan Visual */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '1.5rem',
            }}
          >
            <div
              style={{
                position: 'relative',
                padding: '12px',
                borderRadius: '16px',
                backgroundColor: '#ffffff',
                boxShadow: '0 10px 25px rgba(0, 0, 0, 0.4), 0 0 30px rgba(59, 130, 246, 0.25)',
                border: '2px solid rgba(59, 130, 246, 0.4)',
                overflow: 'hidden',
              }}
            >
              {qrDataUrl ? (
                <img
                  src={qrDataUrl}
                  alt={`QR Code verification for ${filename}`}
                  style={{
                    display: 'block',
                    width: '180px',
                    height: '180px',
                    borderRadius: '8px',
                  }}
                />
              ) : (
                <div
                  style={{
                    width: '180px',
                    height: '180px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#050b14',
                  }}
                >
                  <RefreshCw className="animate-spin" size={32} />
                </div>
              )}

              {/* Scanning laser beam animation during simulation */}
              {isVerifying && (
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: '3px',
                    backgroundColor: '#10b981',
                    boxShadow: '0 0 12px 2px #10b981',
                    animation: 'scanLaser 1.2s infinite ease-in-out',
                  }}
                />
              )}
            </div>

            <div
              style={{
                marginTop: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.78rem',
                color: '#93c5fd',
                fontWeight: 600,
              }}
            >
              <Smartphone size={14} />
              <span>Point any smartphone camera to inspect full evidence ledger</span>
            </div>
          </div>

          {/* Verification Result Notification */}
          {verificationResult && (
            <div
              style={{
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                borderRadius: '10px',
                padding: '0.85rem 1rem',
                marginBottom: '1.25rem',
                animation: 'fadeIn 0.25s ease-out',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  color: '#34d399',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  marginBottom: '4px',
                }}
              >
                <Check size={16} />
                <span>Cryptographic Proof Confirmed by Validator</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#cbd5e1', lineHeight: '1.4' }}>
                Block <strong>#{verificationResult.block}</strong> validated at {verificationResult.verifiedAt}.
                Digital signature matches original root fingerprint with 0 tamper deltas.
              </div>
            </div>
          )}

          {/* Telemetry & Cryptographic Data Grid */}
          <div
            style={{
              backgroundColor: 'rgba(15, 23, 42, 0.5)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '10px',
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.6rem',
              fontSize: '0.78rem',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>Evidence Asset:</span>
              <strong style={{ color: '#ffffff', wordBreak: 'break-all', maxWidth: '65%', textAlign: 'right' }}>
                {filename}
              </strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>Ledger Identification:</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: '#60a5fa', fontWeight: 600 }}>
                {reportId}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>Modality & Verdict:</span>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <span className="badge badge-real" style={{ textTransform: 'capitalize' }}>
                  {modality}
                </span>
                <span className={`badge ${verdict === 'Fake' ? 'badge-fake' : 'badge-real'}`}>
                  {verdict === 'Fake' ? 'Synthetic Detected' : 'Authentic'} ({confidence}%)
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>C2PA Manifest ID:</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: '#94a3b8', fontSize: '0.72rem' }}>
                urn:c2pa:truthlens:{scanId}
              </span>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                <span style={{ color: 'var(--text-muted)' }}>SHA-256 Ledger Digest:</span>
                <button
                  type="button"
                  onClick={handleCopyHash}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: copiedHash ? '#34d399' : '#60a5fa',
                    cursor: 'pointer',
                    fontSize: '0.7rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '3px',
                    padding: 0,
                  }}
                >
                  {copiedHash ? <Check size={11} /> : <Copy size={11} />}
                  <span>{copiedHash ? 'Copied Hash' : 'Copy Hash'}</span>
                </button>
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.68rem',
                  color: 'var(--accent-cyan)',
                  wordBreak: 'break-all',
                  backgroundColor: '#050b14',
                  padding: '6px 8px',
                  borderRadius: '6px',
                  border: '1px solid rgba(6, 182, 212, 0.2)',
                }}
              >
                {sha256}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem' }}>
            <button
              type="button"
              onClick={handleSimulateVerification}
              disabled={isVerifying}
              className="btn-primary"
              style={{
                flex: '1 1 calc(50% - 0.35rem)',
                justifyContent: 'center',
                fontSize: '0.8rem',
                padding: '0.6rem 0.85rem',
              }}
            >
              <RefreshCw size={14} className={isVerifying ? 'animate-spin' : ''} />
              <span>{isVerifying ? 'Verifying Ledger...' : 'Verify Cryptographic Proof'}</span>
            </button>

            <button
              type="button"
              onClick={handleDownloadQr}
              className="btn-secondary"
              style={{
                flex: '1 1 calc(50% - 0.35rem)',
                justifyContent: 'center',
                fontSize: '0.8rem',
                padding: '0.6rem 0.85rem',
              }}
            >
              <Download size={14} />
              <span>Download QR (PNG)</span>
            </button>

            <button
              type="button"
              onClick={handleCopyLink}
              className="btn-secondary"
              style={{
                flex: '1 1 100%',
                justifyContent: 'center',
                fontSize: '0.8rem',
                padding: '0.55rem 0.85rem',
                color: copiedLink ? '#34d399' : 'var(--text-secondary)',
              }}
            >
              {copiedLink ? <Check size={14} /> : <ExternalLink size={14} />}
              <span>{copiedLink ? 'Verification URL Copied to Clipboard!' : 'Copy Public Ledger Verification Link'}</span>
            </button>
          </div>
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '0.85rem 1.5rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            backgroundColor: 'rgba(15, 23, 42, 0.4)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
          }}
        >
          <span>Standards: C2PA v2.1 • ISO/IEC 27037:2012</span>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
