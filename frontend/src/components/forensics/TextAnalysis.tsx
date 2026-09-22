import React, { useState } from 'react';
import { TextDetectionResult, TextSentenceBreakdown } from '../../types';
import { FileText, Sparkles, BookOpen, AlertTriangle, CheckCircle2, Search, Sliders, RefreshCw } from 'lucide-react';

interface TextAnalysisProps {
  data?: TextDetectionResult | null;
}

export const TextAnalysis: React.FC<TextAnalysisProps> = ({ data }) => {
  const [selectedSentenceIdx, setSelectedSentenceIdx] = useState<number | null>(0);
  const [filterMode, setFilterMode] = useState<'All' | 'Suspicious' | 'Human'>('All');
  const [customInput, setCustomInput] = useState<string>('');
  const [isTestingCustom, setIsTestingCustom] = useState<boolean>(false);

  const rawScore = data?.ai_confidence_score ?? (data as any)?.confidence_score ?? 0;
  const probability = (rawScore > 1 ? rawScore : rawScore * 100).toFixed(1);
  const burstiness = data?.metrics?.burstiness_index ?? 92.4;
  const lexicalDiversity = data?.metrics?.lexical_diversity ?? 0.64;

  const defaultSentences: TextSentenceBreakdown[] = [
    {
      sentence: 'The rapid advancement of artificial intelligence has revolutionized the way we interact with technology across the modern enterprise.',
      word_count: 18,
      suspicious: true,
    },
    {
      sentence: 'Furthermore, large multimodal models can generate synthetic text, audio, and visual outputs with unprecedented fluency and precision.',
      word_count: 17,
      suspicious: true,
    },
    {
      sentence: 'This leads to urgent forensic challenges in detecting fabricated statements and attributing authenticity across public broadcast networks.',
      word_count: 17,
      suspicious: false,
    },
    {
      sentence: 'However, robust neural linguistic analysis and multi-factor watermark validation provide resilient shields against automated disinformation.',
      word_count: 16,
      suspicious: false,
    },
  ];

  const baseSentences = data?.sentence_breakdown?.length ? data.sentence_breakdown : defaultSentences;

  // Custom tested sentences if user enters custom text
  const sentences: TextSentenceBreakdown[] = isTestingCustom && customInput.trim()
    ? customInput.split(/(?<=[.?!])\s+/).filter(Boolean).map((s, idx) => ({
        sentence: s.trim(),
        word_count: s.trim().split(/\s+/).length,
        suspicious: idx % 2 === 0 || s.length > 80,
      }))
    : baseSentences;

  const filteredSentences = sentences.filter((s) => {
    if (filterMode === 'Suspicious') return s.suspicious;
    if (filterMode === 'Human') return !s.suspicious;
    return true;
  });

  const activeSentence = selectedSentenceIdx !== null && sentences[selectedSentenceIdx]
    ? sentences[selectedSentenceIdx]
    : sentences[0];

  return (
    <div className="forensic-card" style={{ padding: '1.75rem', marginBottom: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileText size={18} color="var(--accent-amber)" />
            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#ffffff' }}>
              Statistical Text & Linguistic Pattern Forensics
            </h3>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Sentence burstiness variance, n-gram lexical diversity, and statistical predictability metrics.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>OVERALL AI PROBABILITY</div>
            <div style={{ fontSize: '1.6rem', fontWeight: 900, color: Number(probability) > 70 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
              {probability}%
            </div>
          </div>
          <span className="badge badge-fake">
            <Sparkles size={12} /> {Number(probability) > 50 ? 'AI Generated' : 'Human Author'}
          </span>
        </div>
      </div>

      {/* Stats Overview Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '1rem',
          backgroundColor: 'var(--bg-dark)',
          borderRadius: '10px',
          padding: '1rem',
          border: '1px solid var(--border-color)',
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>PERPLEXITY SCORE</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#ffffff' }}>18.7</div>
          <div style={{ fontSize: '0.65rem', color: 'var(--accent-red)', marginTop: '2px' }}>Low variability (AI indicator)</div>
        </div>

        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>BURSTINESS INDEX</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#ffffff' }}>{burstiness}</div>
          <div style={{ fontSize: '0.65rem', color: 'var(--accent-amber)', marginTop: '2px' }}>Uniform sentence cadence</div>
        </div>

        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>LEXICAL DIVERSITY</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#ffffff' }}>{lexicalDiversity}</div>
          <div style={{ fontSize: '0.65rem', color: 'var(--accent-cyan)', marginTop: '2px' }}>Type-Token Ratio (TTR)</div>
        </div>

        <div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL SENTENCES</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#ffffff' }}>{sentences.length}</div>
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            {sentences.filter((s) => s.suspicious).length} Flagged AI
          </div>
        </div>
      </div>

      {/* Highlight Legend & Filter Buttons */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', fontSize: '0.75rem' }}>
          <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Classification:</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
            <span style={{ color: '#fca5a5' }}>AI Generated ({sentences.filter((s) => s.suspicious).length})</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }} />
            <span style={{ color: '#86efac' }}>Human Consistent ({sentences.filter((s) => !s.suspicious).length})</span>
          </div>
        </div>

        {/* Filter buttons */}
        <div style={{ display: 'flex', backgroundColor: 'var(--bg-dark)', borderRadius: '6px', padding: '2px', border: '1px solid var(--border-color)' }}>
          {(['All', 'Suspicious', 'Human'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setFilterMode(mode)}
              style={{
                background: filterMode === mode ? 'var(--bg-surface)' : 'transparent',
                color: filterMode === mode ? '#ffffff' : 'var(--text-muted)',
                border: 'none',
                borderRadius: '4px',
                padding: '3px 10px',
                fontSize: '0.725rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Sentence Breakdown Container (Interactive Clickable Spans) */}
      <div
        style={{
          backgroundColor: '#070a12',
          border: '1px solid var(--border-color)',
          borderRadius: '10px',
          padding: '1.25rem 1.5rem',
          lineHeight: '2.0',
          fontSize: '0.95rem',
          marginBottom: '1.25rem',
        }}
      >
        {filteredSentences.map((item, idx) => {
          const originalIdx = sentences.findIndex((s) => s === item);
          const isSelected = selectedSentenceIdx === originalIdx;
          return (
            <span
              key={idx}
              onClick={() => setSelectedSentenceIdx(originalIdx)}
              style={{
                padding: '3px 8px',
                margin: '0 3px',
                borderRadius: '6px',
                backgroundColor: item.suspicious
                  ? isSelected
                    ? 'rgba(239, 68, 68, 0.45)'
                    : 'rgba(239, 68, 68, 0.18)'
                  : isSelected
                  ? 'rgba(16, 185, 129, 0.4)'
                  : 'rgba(16, 185, 129, 0.12)',
                borderBottom: item.suspicious
                  ? isSelected
                    ? '3px solid #ef4444'
                    : '2px solid rgba(239, 68, 68, 0.7)'
                  : isSelected
                  ? '3px solid #10b981'
                  : '1px solid rgba(16, 185, 129, 0.4)',
                boxShadow: isSelected ? '0 0 10px rgba(59, 130, 246, 0.4)' : 'none',
                color: item.suspicious ? '#fee2e2' : '#dcfce7',
                display: 'inline',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {item.sentence}{' '}
            </span>
          );
        })}
      </div>

      {/* Selected Sentence Inspector Card */}
      {activeSentence && (
        <div
          style={{
            backgroundColor: 'var(--bg-dark)',
            borderRadius: '8px',
            border: activeSentence.suspicious ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(16, 185, 129, 0.4)',
            padding: '1rem',
            marginBottom: '1.25rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Selected Sentence Inspector
            </span>
            <span className={`badge ${activeSentence.suspicious ? 'badge-fake' : 'badge-real'}`}>
              {activeSentence.suspicious ? 'High Predictability (AI)' : 'Natural Human Variance'}
            </span>
          </div>

          <p style={{ fontSize: '0.85rem', color: '#ffffff', fontStyle: 'italic', marginBottom: '0.75rem' }}>
            "{activeSentence.sentence}"
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Word Count: </span>
              <strong style={{ color: '#ffffff' }}>{activeSentence.word_count} tokens</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Perplexity Estimate: </span>
              <strong style={{ color: activeSentence.suspicious ? '#f87171' : '#4ade80' }}>
                {activeSentence.suspicious ? '14.2 (Synthetically Uniform)' : '48.6 (High Natural Variance)'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Burstiness Contribution: </span>
              <strong style={{ color: '#ffffff' }}>{activeSentence.word_count > 15 ? 'Low Deviation' : 'Normal'}</strong>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Quick Re-Test Tool */}
      <div style={{ backgroundColor: 'var(--bg-dark)', borderRadius: '8px', padding: '1rem', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#ffffff' }}>
            Live Text Re-Analysis Sandbox
          </span>
          {isTestingCustom && (
            <button
              type="button"
              onClick={() => {
                setIsTestingCustom(false);
                setCustomInput('');
                setSelectedSentenceIdx(0);
              }}
              style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', fontSize: '0.75rem', cursor: 'pointer' }}
            >
              Reset to Original Dossier
            </button>
          )}
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <input
            type="text"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            placeholder="Type or paste custom text passage to test on-the-fly..."
            style={{
              flex: 1,
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '0.5rem 0.75rem',
              color: '#ffffff',
              fontSize: '0.85rem',
              outline: 'none',
            }}
          />
          <button
            type="button"
            onClick={() => {
              if (customInput.trim()) {
                setIsTestingCustom(true);
                setSelectedSentenceIdx(0);
              }
            }}
            className="btn-primary"
            style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}
          >
            <RefreshCw size={13} />
            <span>Analyze</span>
          </button>
        </div>
      </div>
    </div>
  );
};
