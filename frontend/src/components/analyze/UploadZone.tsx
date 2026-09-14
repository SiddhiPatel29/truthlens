import React, { useState, useRef } from 'react';
import { Film, Mic, Image as ImageIcon, FileText, UploadCloud, X, AlertCircle } from 'lucide-react';

interface UploadZoneProps {
  onStartAnalysis: (modality: 'video' | 'audio' | 'image' | 'text', fileOrText: File | string) => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onStartAnalysis }) => {
  const [selectedModality, setSelectedModality] = useState<'video' | 'audio' | 'image' | 'text'>('video');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [textContent, setTextContent] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const modalityTabs = [
    { id: 'video', label: 'Video', icon: Film, accept: '.mp4,.mov,.avi,.mkv' },
    { id: 'audio', label: 'Audio', icon: Mic, accept: '.wav' },
    { id: 'image', label: 'Image', icon: ImageIcon, accept: '.jpg,.jpeg,.png,.webp' },
    { id: 'text', label: 'Text', icon: FileText, accept: '' },
  ] as const;

  const handleFileChange = (file: File) => {
    setError(null);
    if (selectedModality === 'audio' && !file.name.toLowerCase().endsWith('.wav')) {
      setError('Audio analysis currently supports .WAV format only.');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError('File size exceeds the 50 MB server limit.');
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) 
    {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = () => {
    setError(null);
    if (selectedModality === 'text') 
    {
      if (textContent.trim().length < 20) 
      {
        setError('Please enter at least 20 characters for forensic text analysis.');
        return;
      }
      onStartAnalysis('text', textContent);
    } 
    else 
    {
      if (!selectedFile) 
      {
        setError('Please select a file to analyze.');
        return;
      }
      onStartAnalysis(selectedModality, selectedFile);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="forensic-card" style={{ maxWidth: '780px', margin: '0 auto', padding: '2rem' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.35rem' }}>
          Select Analysis Modality
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Choose a media category and provide content to run deepfake detection models.
        </p>
      </div>

      {/* Modality Tabs (Frame 3) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '0.75rem',
          marginBottom: '1.75rem',
        }}
      >
        {modalityTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = selectedModality === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setSelectedModality(tab.id);
                setSelectedFile(null);
                setError(null);
              }}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.85rem 0.5rem',
                borderRadius: '10px',
                border: isActive ? '2px solid var(--accent-blue)' : '1px solid var(--border-color)',
                backgroundColor: isActive ? 'rgba(59, 130, 246, 0.12)' : 'var(--bg-dark)',
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={22} color={isActive ? 'var(--accent-blue)' : 'var(--text-secondary)'} />
              <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {error && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            color: '#fca5a5',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '1.25rem',
          }}
        >
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Zone or Text Area (Frame 3) */}
      {selectedModality === 'text' ? (
        <div style={{ marginBottom: '1.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.8rem' }}>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Text Content to Evaluate</span>
            <span style={{ color: textContent.length > 25000 ? 'var(--accent-red)' : 'var(--text-muted)' }}>
              {textContent.length.toLocaleString()} / 25,000 characters
            </span>
          </div>
          <textarea
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
            rows={7}
            placeholder="Paste suspected AI-generated text, article, or statement here to calculate perplexity, sentence burstiness, and entropy..."
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-dark)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '1rem',
              color: '#ffffff',
              fontSize: '0.9rem',
              outline: 'none',
              resize: 'vertical',
              fontFamily: 'inherit',
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setTextContent(
                  'The rapid advancement of artificial intelligence and deep neural networks has fundamentally transformed digital communication across global networks. Modern generative architectures can synthesize remarkably fluent prose, mimicking human journalistic tone with minimal lexical divergence. Forensic entropy scoring is essential to verify authenticity.'
                );
              }}
              style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem', borderColor: 'var(--accent-amber)', color: '#fcd34d' }}
            >
              ⚡ Load Sample AI Text
            </button>
          </div>
        </div>
      ) : (
        <div style={{ marginBottom: '1.75rem' }}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
            accept={modalityTabs.find((m) => m.id === selectedModality)?.accept}
            style={{ display: 'none' }}
          />

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: dragOver ? '2px dashed var(--accent-blue)' : '2px dashed #334155',
              backgroundColor: dragOver ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-dark)',
              borderRadius: '12px',
              padding: '2.5rem 1.5rem',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: 'var(--bg-surface)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem',
                color: 'var(--accent-blue)',
              }}
            >
              <UploadCloud size={28} />
            </div>

            <div style={{ fontSize: '1rem', fontWeight: 600, color: '#ffffff', marginBottom: '0.25rem' }}>
              Drag & Drop your {selectedModality} file here
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              or click to browse your computer
            </div>

            <button
              type="button"
              className="btn-secondary"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
            >
              Browse Files
            </button>

            {selectedModality === 'audio' && (
              <div style={{ marginTop: '0.75rem', fontSize: '0.725rem', color: 'var(--accent-amber)' }}>
                * WAV audio format only
              </div>
            )}
          </div>

          {/* Selected File Pill */}
          {selectedFile && (
            <div
              style={{
                marginTop: '1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem 1rem',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Film size={20} color="var(--accent-blue)" />
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>
                    {selectedFile.name}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {formatFileSize(selectedFile.size)} • Ready for analysis
                  </div>
                </div>
              </div>

              <button
                onClick={() => setSelectedFile(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Start Button */}
      <button
        onClick={handleSubmit}
        className="btn-primary"
        style={{
          width: '100%',
          padding: '0.85rem',
          fontSize: '1rem',
        }}
      >
        Start Forensic Analysis
      </button>

      <div style={{ textAlign: 'center', marginTop: '0.75rem', fontSize: '0.725rem', color: 'var(--text-muted)' }}>
        By submitting media, verification runs under C2PA-Authenticity and NIST-AI-100-2 forensic standards.
      </div>
    </div>
  );
};
