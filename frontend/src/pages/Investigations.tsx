import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { HeatmapViewer } from '../components/forensics/HeatmapViewer';
import { VideoForensics } from '../components/forensics/VideoForensics';
import { AudioLipSync } from '../components/forensics/AudioLipSync';
import { ImageForensics } from '../components/forensics/ImageForensics';
import { TextAnalysis } from '../components/forensics/TextAnalysis';
import { ChainOfCustody } from '../components/investigation/ChainOfCustody';
import { RiskAssessment } from '../components/investigation/RiskAssessment';
import { HumanReview } from '../components/investigation/HumanReview';
import { getScanRecord, ForensicScanRecord } from '../utils/scanManager';
import {
  FileText,
  Film,
  Mic,
  Image as ImageIcon,
  FolderLock,
  Layers,
  ShieldAlert,
  Send,
  ExternalLink,
  Download,
  Eye,
  CheckCircle2,
  Calendar,
  User,
  Sliders,
} from 'lucide-react';

export const Investigations: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const scanId = searchParams.get('scanId') || '821';
  const initialTab = (searchParams.get('tab') as any) || 'Overview';
  const [activeTab, setActiveTab] = useState<'Overview' | 'Evidence' | 'Forensics' | 'Timeline' | 'Review'>(
    ['Overview', 'Evidence', 'Forensics', 'Timeline', 'Review'].includes(initialTab) ? initialTab : 'Overview'
  );

  const [scanRecord, setScanRecord] = useState<ForensicScanRecord | null>(null);
  const [forensicFilter, setForensicFilter] = useState<'focused' | 'all'>('focused');

  useEffect(() => {
    const record = getScanRecord(scanId);
    setScanRecord(record);
  }, [scanId]);

  const modality = scanRecord?.media_type || 'video';
  const isSynthetic = scanRecord?.prediction === 'Fake';
  const confidence = scanRecord?.confidence || 98.2;
  const filename = scanRecord?.filename || 'evidence_asset.mp4';
  const filesize = scanRecord?.filesize || '18.4 MB';
  const sha256 = scanRecord?.sha256 || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';

  // Dynamic Case Title & Inquest Description based on uploaded modality
  const caseHeader =
    modality === 'video'
      ? {
          title: 'Synthetic Identity Deepfake & Video Tampering Inquest',
          desc: 'Bi-LSTM inter-frame sequence temporal jitter and Grad-CAM++ facial landmark boundary analysis.',
          icon: Film,
        }
      : modality === 'audio'
      ? {
          title: 'Acoustic Voice Synthesis & Phoneme Desync Inquest',
          desc: 'SyncNet acoustic-phonemic viseme correlation and neural vocoder spectral discrepancy.',
          icon: Mic,
        }
      : modality === 'image'
      ? {
          title: 'Spatial Tampering & Pixel Residual Inquest',
          desc: 'Error Level Analysis (ELA), Laplacian high-pass noise residual, and ResNet-50 feature activation maps.',
          icon: ImageIcon,
        }
      : {
          title: 'Neural Linguistic & LLM Synthetics Inquest',
          desc: 'RoBERTa token perplexity estimation, sentence burstiness variance, and n-gram lexical diversity.',
          icon: FileText,
        };

  // Dynamic Evidence files matching the uploaded media
  const getEvidenceFiles = () => {
    if (modality === 'video') {
      return [
        { name: filename, size: filesize, icon: Film, type: 'Video Source Asset', hash: sha256 },
        { name: `extracted_keyframe_018.jpg`, size: '1.8 MB', icon: ImageIcon, type: 'Keyframe Anomaly', hash: sha256.slice(0, 32) + '1818' },
        { name: `gradcam_heatmap_layer4.png`, size: '2.4 MB', icon: Layers, type: 'Spatial Heatmap', hash: sha256.slice(0, 32) + '4444' },
        { name: `extracted_audio_track.wav`, size: '1.2 MB', icon: Mic, type: 'Acoustic Track', hash: sha256.slice(0, 32) + '2222' },
        { name: `forensic_c2pa_dossier_VM-${scanId}.pdf`, size: '2.4 MB', icon: FileText, type: 'Evidence Dossier', hash: sha256.slice(0, 32) + '9999' },
      ];
    }
    if (modality === 'audio') {
      return [
        { name: filename, size: filesize, icon: Mic, type: 'Audio WAV Source Asset', hash: sha256 },
        { name: `spectrogram_spectrum.png`, size: '1.4 MB', icon: Layers, type: 'Mel-Spectrogram Map', hash: sha256.slice(0, 32) + '3333' },
        { name: `syncnet_discrepancy_log.json`, size: '28 KB', icon: FileText, type: 'Formant Viseme Log', hash: sha256.slice(0, 32) + '7777' },
        { name: `forensic_c2pa_dossier_VM-${scanId}.pdf`, size: '2.1 MB', icon: FileText, type: 'Evidence Dossier', hash: sha256.slice(0, 32) + '9999' },
      ];
    }
    if (modality === 'image') {
      return [
        { name: filename, size: filesize, icon: ImageIcon, type: 'Source Image Asset', hash: sha256 },
        { name: `gradcam_spatial_heatmap.png`, size: '2.4 MB', icon: Layers, type: 'Spatial Activation Map', hash: sha256.slice(0, 32) + '4444' },
        { name: `ela_compression_residual.jpg`, size: '1.6 MB', icon: ImageIcon, type: 'ELA Error Level Map', hash: sha256.slice(0, 32) + '5555' },
        { name: `exif_c2pa_provenance.json`, size: '12 KB', icon: FileText, type: 'Cryptographic Provenance', hash: sha256.slice(0, 32) + '8888' },
        { name: `forensic_c2pa_dossier_VM-${scanId}.pdf`, size: '2.2 MB', icon: FileText, type: 'Evidence Dossier', hash: sha256.slice(0, 32) + '9999' },
      ];
    }
    return [
      { name: filename, size: filesize, icon: FileText, type: 'Submitted Text Document', hash: sha256 },
      { name: `roberta_token_entropy.json`, size: '36 KB', icon: FileText, type: 'Perplexity Matrix', hash: sha256.slice(0, 32) + '6666' },
      { name: `burstiness_breakdown.csv`, size: '8 KB', icon: FileText, type: 'Sentence Burstiness Metrics', hash: sha256.slice(0, 32) + '1111' },
      { name: `forensic_c2pa_dossier_VM-${scanId}.pdf`, size: '1.9 MB', icon: FileText, type: 'Evidence Dossier', hash: sha256.slice(0, 32) + '9999' },
    ];
  };

  const evidenceFiles = getEvidenceFiles();

  const handleDownloadFile = (fileName: string) => {
    const dummyBlob = new Blob([`C2PA Certified Evidence Hash for ${fileName}\nSHA-256: ${sha256}\nCase ID: VM-2026-00${scanId}`], { type: 'text/plain' });
    const url = URL.createObjectURL(dummyBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page-container">
      {/* Case Header Banner */}
      <div
        className="forensic-card"
        style={{
          marginBottom: '1.75rem',
          padding: '1.5rem 2rem',
          background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.95) 0%, rgba(30, 41, 59, 0.6) 100%)',
          border: '1px solid #334155',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.25rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>INVESTIGATION WORKSPACE</span>
              <span className="badge" style={{ backgroundColor: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
                ACTIVE INQUEST
              </span>
              <span className={`badge ${isSynthetic ? 'badge-critical' : 'badge-real'}`}>
                {scanRecord?.risk_level || 'CRITICAL'} THREAT ({confidence}%)
              </span>
            </div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 900, color: '#ffffff', letterSpacing: '-0.025em' }}>
              CASE #VM-2026-00{scanId}
            </h1>
            <p style={{ fontSize: '0.9rem', color: '#93c5fd', marginTop: '2px' }}>
              {caseHeader.title}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => navigate(`/abuse?scanId=${scanId}&confidence=${confidence}`)}
              className="btn-primary"
            >
              <Send size={16} />
              <span>Escalate Takedown</span>
            </button>
            <button
              type="button"
              onClick={() => navigate(`/reports?reportId=VM-2026-00${scanId}`)}
              className="btn-secondary"
            >
              <FileText size={16} />
              <span>Export Dossier</span>
            </button>
          </div>
        </div>

        {/* Sub-Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem', overflowX: 'auto' }}>
          {(['Overview', 'Evidence', 'Forensics', 'Timeline', 'Review'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              style={{
                background: activeTab === tab ? 'var(--bg-surface)' : 'transparent',
                color: activeTab === tab ? '#ffffff' : 'var(--text-secondary)',
                border: activeTab === tab ? '1px solid var(--accent-blue)' : '1px solid transparent',
                borderRadius: '6px',
                padding: '0.45rem 1rem',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Tab: Overview */}
      {activeTab === 'Overview' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem', marginBottom: '1.75rem' }}>
            {/* Case Evidentiary Files */}
            <div className="forensic-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>Case Evidentiary Assets</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{evidenceFiles.length} Assets Anchored</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                {evidenceFiles.map((f, i) => {
                  const Icon = f.icon;
                  return (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0.75rem 1rem',
                        backgroundColor: 'var(--bg-dark)',
                        borderRadius: '8px',
                        border: '1px solid var(--border-color)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Icon size={18} color="var(--accent-blue)" />
                        <div>
                          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>{f.name}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{f.size} • {f.type}</div>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleDownloadFile(f.name)}
                        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                        title="Download Asset"
                      >
                        <Download size={15} />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Case Summary Card matching uploaded file */}
            <div className="forensic-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>Inquest Summary Details</h3>
                <span className={`badge ${isSynthetic ? 'badge-critical' : 'badge-real'}`}>
                  Confidence: {confidence}%
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '0.4rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Analyzed Target Media</span>
                  <strong style={{ color: '#93c5fd', wordBreak: 'break-all', maxWidth: '65%', textAlign: 'right' }}>
                    {filename}
                  </strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '0.4rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Modality</span>
                  <span style={{ fontWeight: 600, color: '#ffffff', textTransform: 'capitalize' }}>{modality} Analysis</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '0.4rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Creation Timestamp</span>
                  <span style={{ fontWeight: 600, color: '#ffffff' }}>
                    {new Date(scanRecord?.created_at || Date.now()).toUTCString()}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '0.4rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Investigating Examiner</span>
                  <span style={{ fontWeight: 600, color: '#ffffff' }}>Admin / Senior Analyst</span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '0.35rem' }}>Forensic Description</span>
                  <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.5', backgroundColor: 'var(--bg-dark)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    {caseHeader.desc}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Embedded Risk Assessment */}
          <RiskAssessment />
        </>
      )}

      {/* Tab: Forensics (Dynamic Modality Focus) */}
      {activeTab === 'Forensics' && (
        <div>
          {/* Forensic Filter Selector */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', backgroundColor: 'var(--bg-dark)', padding: '0.65rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>
              Showing Diagnostics for: <strong style={{ color: 'var(--accent-blue)', textTransform: 'uppercase' }}>{modality}</strong>
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => setForensicFilter('focused')}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: forensicFilter === 'focused' ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                  backgroundColor: forensicFilter === 'focused' ? 'var(--bg-surface)' : 'transparent',
                  color: forensicFilter === 'focused' ? '#ffffff' : 'var(--text-muted)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                }}
              >
                Relevant Only ({modality})
              </button>
              <button
                type="button"
                onClick={() => setForensicFilter('all')}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: forensicFilter === 'all' ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                  backgroundColor: forensicFilter === 'all' ? 'var(--bg-surface)' : 'transparent',
                  color: forensicFilter === 'all' ? '#ffffff' : 'var(--text-muted)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                }}
              >
                Show All 5 Modality Diagnostics
              </button>
            </div>
          </div>

          {/* Focused rendering based on uploaded media */}
          {forensicFilter === 'focused' ? (
            <>
              {modality === 'video' && (
                <>
                  <HeatmapViewer heatmapUrl={scanRecord?.preview_url} />
                  <VideoForensics data={scanRecord?.raw_result} />
                  <AudioLipSync />
                </>
              )}
              {modality === 'image' && (
                <>
                  <ImageForensics data={scanRecord?.raw_result} />
                  <HeatmapViewer heatmapUrl={scanRecord?.preview_url} />
                </>
              )}
              {modality === 'audio' && (
                <>
                  <AudioLipSync data={scanRecord?.raw_result} />
                </>
              )}
              {modality === 'text' && (
                <>
                  <TextAnalysis data={scanRecord?.raw_result} />
                </>
              )}
            </>
          ) : (
            <>
              <HeatmapViewer heatmapUrl={scanRecord?.preview_url} />
              <VideoForensics data={scanRecord?.raw_result} />
              <AudioLipSync data={scanRecord?.raw_result} />
              <ImageForensics data={scanRecord?.raw_result} />
              <TextAnalysis data={scanRecord?.raw_result} />
            </>
          )}
        </div>
      )}

      {/* Tab: Timeline */}
      {activeTab === 'Timeline' && <ChainOfCustody />}

      {/* Tab: Evidence */}
      {activeTab === 'Evidence' && (
        <div className="forensic-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>Evidentiary Assets Repository</h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Immutable vault assets with SHA-256 tamper validation for Case #VM-2026-00{scanId} ({filename}).
              </p>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
            {evidenceFiles.map((file, i) => (
              <div key={i} style={{ backgroundColor: 'var(--bg-dark)', padding: '1.25rem', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <file.icon size={28} color="var(--accent-blue)" style={{ marginBottom: '0.75rem' }} />
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#ffffff', marginBottom: '2px', wordBreak: 'break-all' }}>{file.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>{file.size} • {file.type}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.675rem', color: '#94a3b8', wordBreak: 'break-all', backgroundColor: '#070a12', padding: '4px 6px', borderRadius: '4px' }}>
                    SHA256: {file.hash}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleDownloadFile(file.name)}
                  className="btn-secondary"
                  style={{ marginTop: '1rem', width: '100%', justifyContent: 'center', fontSize: '0.75rem' }}
                >
                  <Download size={14} />
                  <span>Download Verified Asset</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Review */}
      {activeTab === 'Review' && <HumanReview scanId={scanId} />}
    </div>
  );
};
