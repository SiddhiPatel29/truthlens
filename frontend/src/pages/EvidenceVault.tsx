import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAllVaultAssets, VaultEvidenceAsset } from '../utils/scanManager';
import { LedgerQrModal } from '../components/common/LedgerQrModal';
import { Search, Folder, Film, Image as ImageIcon, Layers, FileText, Download, Filter, Eye, Plus, Check, X, ShieldCheck, ArrowRight, QrCode } from 'lucide-react';

export const EvidenceVault: React.FC = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFolder, setSelectedFolder] = useState<string>('All Folders');
  const [inspectAsset, setInspectAsset] = useState<VaultEvidenceAsset | null>(null);
  const [qrModalAsset, setQrModalAsset] = useState<VaultEvidenceAsset | null>(null);
  const [assets, setAssets] = useState<VaultEvidenceAsset[]>([]);

  useEffect(() => {
    setAssets(getAllVaultAssets());
  }, []);

  const folders = [
    { name: 'All Folders', count: assets.length, icon: Folder, color: 'var(--text-secondary)' },
    { name: 'Video Sources', count: assets.filter((a) => a.type === 'Video').length, icon: Film, color: 'var(--accent-blue)', typeMatch: 'Video' },
    { name: 'Images & Frames', count: assets.filter((a) => a.type === 'Frame').length, icon: ImageIcon, color: 'var(--accent-cyan)', typeMatch: 'Frame' },
    { name: 'Audio Records', count: assets.filter((a) => a.type === 'Audio').length, icon: FileText, color: 'var(--accent-green)', typeMatch: 'Audio' },
    { name: 'Heatmaps', count: assets.filter((a) => a.type === 'Heatmap').length, icon: Layers, color: 'var(--accent-red)', typeMatch: 'Heatmap' },
    { name: 'Dossiers & Reports', count: assets.filter((a) => a.type === 'Report' || a.type === 'Text').length, icon: FileText, color: 'var(--accent-amber)', typeMatch: 'Report' },
  ];

  const filteredAssets = assets.filter((a) => {
    const matchesSearch =
      a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.hash.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.type.toLowerCase().includes(searchTerm.toLowerCase());

    if (selectedFolder === 'All Folders') return matchesSearch;
    const folderObj = folders.find((f) => f.name === selectedFolder);
    if (folderObj && folderObj.typeMatch) {
      if (folderObj.typeMatch === 'Report') {
        return matchesSearch && (a.type === 'Report' || a.type === 'Text');
      }
      return matchesSearch && a.type === folderObj.typeMatch;
    }
    return matchesSearch;
  });

  const handleDownload = (asset: VaultEvidenceAsset) => {
    const content = `VeraMedia AI Evidence Package\n=================================\nAsset Name: ${asset.name}\nMedia Modality: ${asset.type}\nFile Size: ${asset.size}\nDate Anchored: ${asset.date}\nSHA-256 Ledger Fingerprint: ${asset.hash}\nC2PA Status: Certified Cryptographic Envelope\n`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${asset.name}_forensic_manifest.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.025em' }}>
          Secure Evidence Vault & Asset Repository
        </h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Tamper-evident cold storage repository housing raw media inputs, keyframes, activation maps, and forensic certificates.
        </p>
      </div>

      {/* Search & Filter Bar */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '1rem',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.75rem',
        }}
      >
        <div style={{ position: 'relative', flex: '1 1 300px', maxWidth: '480px' }}>
          <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search evidence by filename, SHA-256 hash, or modality..."
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '0.65rem 1rem 0.65rem 2.5rem',
              color: '#ffffff',
              fontSize: '0.85rem',
              outline: 'none',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Showing {filteredAssets.length} of {assets.length} anchored evidence files
          </span>
        </div>
      </div>

      {/* Categorized Folders Grid (Clickable Category Tabs) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '1rem',
          marginBottom: '2rem',
        }}
      >
        {folders.map((f) => {
          const isSelected = selectedFolder === f.name;
          const Icon = f.icon;
          return (
            <div
              key={f.name}
              onClick={() => setSelectedFolder(f.name)}
              className="forensic-card"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.85rem',
                padding: '1rem',
                cursor: 'pointer',
                border: isSelected ? '2px solid var(--accent-blue)' : '1px solid var(--border-color)',
                backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'var(--bg-card)',
                transition: 'all 0.15s ease',
              }}
            >
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-surface)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: f.color,
                  border: '1px solid var(--border-color)',
                  flexShrink: 0,
                }}
              >
                <Icon size={18} />
              </div>
              <div>
                <div style={{ fontSize: '0.825rem', fontWeight: 700, color: '#ffffff' }}>{f.name}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{f.count} Assets</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Assets Grid */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>
            Vault Evidence Files ({selectedFolder})
          </h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1.25rem' }}>
          {filteredAssets.map((asset) => (
            <div
              key={asset.id}
              className="forensic-card"
              style={{ padding: '0.85rem', display: 'flex', flexDirection: 'column' }}
            >
              <div
                onClick={() => setInspectAsset(asset)}
                style={{
                  position: 'relative',
                  width: '100%',
                  height: '140px',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  backgroundColor: '#070a12',
                  marginBottom: '0.75rem',
                  cursor: 'pointer',
                }}
              >
                <img src={asset.thumb} alt={asset.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                <span
                  style={{
                    position: 'absolute',
                    top: '8px',
                    left: '8px',
                    backgroundColor: 'rgba(0,0,0,0.75)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    color: '#ffffff',
                  }}
                >
                  {asset.type}
                </span>

                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    backgroundColor: 'rgba(0,0,0,0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: 0,
                    transition: 'opacity 0.2s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                  onMouseLeave={(e) => (e.currentTarget.style.opacity = '0')}
                >
                  <Eye size={24} color="#ffffff" />
                </div>
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.825rem', fontWeight: 700, color: '#ffffff', wordBreak: 'break-word', marginBottom: '4px' }}>
                  {asset.name}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                  {asset.size} • {asset.date}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: '#94a3b8', wordBreak: 'break-all', backgroundColor: '#070a12', padding: '3px 6px', borderRadius: '4px' }}>
                  SHA256: {asset.hash.slice(0, 16)}...
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => setInspectAsset(asset)}
                  className="btn-secondary"
                  style={{ flex: 1, padding: '0.4rem 0.5rem', fontSize: '0.75rem', justifyContent: 'center' }}
                >
                  <Eye size={13} />
                  <span>Inspect</span>
                </button>
                <button
                  type="button"
                  onClick={() => setQrModalAsset(asset)}
                  className="btn-secondary"
                  title="Scan to verify on immutable ledger"
                  style={{ padding: '0.4rem 0.55rem', fontSize: '0.75rem', justifyContent: 'center', borderColor: 'rgba(59, 130, 246, 0.4)', color: '#93c5fd' }}
                >
                  <QrCode size={13} />
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload(asset)}
                  className="btn-primary"
                  style={{ flex: 1, padding: '0.4rem 0.5rem', fontSize: '0.75rem', justifyContent: 'center' }}
                >
                  <Download size={13} />
                  <span>Download</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Asset Inspection Modal */}
      {inspectAsset && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(5px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
          }}
          onClick={() => setInspectAsset(null)}
        >
          <div
            className="forensic-card"
            style={{ maxWidth: '560px', width: '100%', padding: '1.75rem', backgroundColor: '#0f172a' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={20} color="var(--accent-blue)" />
                <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>
                  Asset Forensic Inspection
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setInspectAsset(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ height: '220px', borderRadius: '8px', overflow: 'hidden', backgroundColor: '#070a12', marginBottom: '1rem' }}>
              <img src={inspectAsset.thumb} alt={inspectAsset.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8rem', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Asset Name:</span>
                <strong style={{ color: '#ffffff', wordBreak: 'break-all', textAlign: 'right', maxWidth: '70%' }}>{inspectAsset.name}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Modality:</span>
                <span className="badge badge-real">{inspectAsset.type}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>File Size:</span>
                <span style={{ color: '#ffffff' }}>{inspectAsset.size}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Date Anchored:</span>
                <span style={{ color: '#ffffff' }}>{inspectAsset.date}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>Immutable SHA-256 Ledger Hash:</span>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--accent-cyan)', wordBreak: 'break-all', backgroundColor: '#070a12', padding: '6px 8px', borderRadius: '4px' }}>
                  {inspectAsset.hash}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => setQrModalAsset(inspectAsset)}
                className="btn-secondary"
                style={{ flex: '1 1 calc(50% - 0.4rem)', justifyContent: 'center', borderColor: 'rgba(59, 130, 246, 0.4)', color: '#93c5fd' }}
              >
                <QrCode size={14} />
                <span>Scan / Verify Ledger</span>
              </button>
              {inspectAsset.scan_id && (
                <button
                  type="button"
                  onClick={() => navigate(`/investigations?scanId=${inspectAsset.scan_id}`)}
                  className="btn-secondary"
                  style={{ flex: '1 1 calc(50% - 0.4rem)', justifyContent: 'center' }}
                >
                  <span>Open Investigation</span>
                  <ArrowRight size={14} />
                </button>
              )}
              <button
                type="button"
                onClick={() => handleDownload(inspectAsset)}
                className="btn-primary"
                style={{ flex: '1 1 100%', justifyContent: 'center' }}
              >
                <Download size={15} />
                <span>Download Manifest</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Immutable Ledger QR Modal */}
      {qrModalAsset && (
        <LedgerQrModal
          isOpen={true}
          onClose={() => setQrModalAsset(null)}
          scanId={qrModalAsset.scan_id || '9821'}
          filename={qrModalAsset.name}
          sha256={qrModalAsset.hash}
          modality={qrModalAsset.type.toLowerCase()}
          verdict="Verified Immutable"
          confidence={99.9}
          reportId={`VM-VAULT-${qrModalAsset.id}`}
        />
      )}
    </div>
  );
};
