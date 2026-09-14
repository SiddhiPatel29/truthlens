import React, { useState } from 'react';
import { UploadZone } from '../components/analyze/UploadZone';
import { AnalysisProgress } from '../components/analyze/AnalysisProgress';
import { DetectionResult } from '../components/analyze/DetectionResult';
import { detectVideo, detectAudio, detectImage, detectText } from '../api/detection';
import { registerNewScan, ForensicScanRecord } from '../utils/scanManager';
import { AlertCircle } from 'lucide-react';

export const Analyze: React.FC = () => {
  const [stage, setStage] = useState<'upload' | 'analyzing' | 'result'>('upload');
  const [activeModality, setActiveModality] = useState<'video' | 'audio' | 'image' | 'text'>('video');
  const [detectionResult, setDetectionResult] = useState<any>(null);
  const [activeScanRecord, setActiveScanRecord] = useState<ForensicScanRecord | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleStartAnalysis = async (
    modality: 'video' | 'audio' | 'image' | 'text',
    fileOrText: File | string
  ) => {
    setActiveModality(modality);
    setErrorMsg(null);
    setStage('analyzing');

    try {
      let res;
      if (modality === 'video' && fileOrText instanceof File) {
        res = await detectVideo(fileOrText);
      } else if (modality === 'audio' && fileOrText instanceof File) {
        res = await detectAudio(fileOrText);
      } else if (modality === 'image' && fileOrText instanceof File) {
        res = await detectImage(fileOrText);
      } else if (modality === 'text' && typeof fileOrText === 'string') {
        res = await detectText(fileOrText);
      } else {
        throw new Error('Invalid upload payload.');
      }

      if (res && res.success) {
        setDetectionResult(res.data);
        // Register newly analyzed scan across app (Investigations, Reports, Vault, History)
        const newRecord = registerNewScan(modality, fileOrText, res.data);
        setActiveScanRecord(newRecord);
        setStage('result');
      } else {
        throw new Error(res?.message || 'Detection failed.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Analysis encountered an unexpected server error.');
      setStage('upload');
    }
  };

  const handleReset = () => {
    setDetectionResult(null);
    setActiveScanRecord(null);
    setErrorMsg(null);
    setStage('upload');
  };

  return (
    <div className="page-container">
      {/* Top Banner Navigation */}
      <div style={{ marginBottom: '1.75rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.025em' }}>
          Deepfake & Authenticity Analysis Console
        </h1>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Submit video, audio, image, or textual content to execute multi-modal verification pipelines.
        </p>
      </div>

      {errorMsg && (
        <div
          style={{
            maxWidth: '780px',
            margin: '0 auto 1.5rem',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            color: '#fca5a5',
            padding: '0.85rem 1.25rem',
            borderRadius: '8px',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
          }}
        >
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Upload Stage */}
      {stage === 'upload' && <UploadZone onStartAnalysis={handleStartAnalysis} />}

      {/* Progress Stage */}
      {stage === 'analyzing' && <AnalysisProgress modality={activeModality} />}

      {/* Result Stage */}
      {stage === 'result' && (
        <DetectionResult
          modality={activeModality}
          result={detectionResult}
          scanRecord={activeScanRecord}
          onReset={handleReset}
        />
      )}
    </div>
  );
};
