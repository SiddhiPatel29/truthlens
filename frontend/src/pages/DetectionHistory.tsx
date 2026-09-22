import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getScans } from '../api/scans';
import { ScanSummary } from '../types';
import { getAllScans, ForensicScanRecord } from '../utils/scanManager';
import { History, Film, Mic, Image as ImageIcon, FileText, ChevronLeft, ChevronRight, ExternalLink, Search, Filter, RefreshCw } from 'lucide-react';

export const DetectionHistory: React.FC = () => {
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [localScans, setLocalScans] = useState<ForensicScanRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [modalityFilter, setModalityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'Reviewed' | 'Complete' | 'Pending'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;
  const navigate = useNavigate();

  async function loadScans() {
    setLoading(true);
    setLocalScans(getAllScans());
    try {
      const res = await getScans();
      const items = Array.isArray(res?.data) ? res.data : (res?.data as any)?.items || [];
      if (res.success && items.length > 0) {
        setScans(items);
      }
    } catch {
      // Fallback to local scans
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadScans();
  }, []);

  const getModalityIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'video': return <Film size={15} color="var(--accent-blue)" />;
      case 'audio': return <Mic size={15} color="var(--accent-cyan)" />;
      case 'image': return <ImageIcon size={15} color="var(--accent-green)" />;
      default: return <FileText size={15} color="var(--accent-amber)" />;
    }
  };

  const formattedLocal = localScans.map((s) => ({
    id: s.id,
    media_type: s.media_type,
    prediction: s.prediction,
    confidence: s.confidence > 1 ? s.confidence / 100 : s.confidence,
    risk: s.risk_level,
    date: new Date(s.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }),
    status: s.status,
  }));

  const formattedApi = scans.map((s) => ({
    id: s.id,
    media_type: s.media_type,
    prediction: s.result?.prediction || 'Fake',
    confidence: s.result?.confidence || 0.95,
    risk: s.result?.risk_level || 'High',
    date: new Date(s.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }),
    status: s.status === 'COMPLETED' ? 'Reviewed' : 'Pending',
  }));

  // Deduplicate by ID prioritizing freshly added local scans
  const mergedMap = new Map<number, any>();
  formattedLocal.forEach((row) => mergedMap.set(row.id, row));
  formattedApi.forEach((row) => {
    if (!mergedMap.has(row.id)) mergedMap.set(row.id, row);
  });
  const rawRows = Array.from(mergedMap.values());

  // Filter rows
  const filteredRows = rawRows.filter((r) => {
    const matchesSearch =
      String(r.id).includes(searchQuery) ||
      r.prediction.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.media_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.risk.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesModality = modalityFilter === 'all' || r.media_type.toLowerCase() === modalityFilter.toLowerCase();
    const matchesStatus = statusFilter === 'all' || r.status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesModality && matchesStatus;
  });

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const displayRows = filteredRows.slice((safePage - 1) * pageSize, safePage * pageSize);

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '1.75rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.025em' }}>
            Forensic Detection History & Audit Ledger
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Historical record of all analyzed media assets, risk levels, model verdicts, and review statuses.
          </p>
        </div>

        <button
          type="button"
          onClick={loadScans}
          className="btn-secondary"
          style={{ padding: '6px 12px', fontSize: '0.8rem' }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Filter and Search Controls Bar */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '1rem',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
        }}
      >
        {/* Search */}
        <div style={{ position: 'relative', flex: '1 1 260px', maxWidth: '400px' }}>
          <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '13px' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search by ID, modality, or risk level..."
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Modality Filter */}
          <select
            value={modalityFilter}
            onChange={(e) => {
              setModalityFilter(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              borderRadius: '8px',
              padding: '0.6rem 1rem',
              fontSize: '0.825rem',
              outline: 'none',
            }}
          >
            <option value="all">All Modalities</option>
            <option value="video">Video Sources</option>
            <option value="image">Images</option>
            <option value="audio">Audio Tracks</option>
            <option value="text">Text Passages</option>
          </select>

          {/* Status Tabs */}
          <div style={{ display: 'flex', backgroundColor: 'var(--bg-dark)', borderRadius: '8px', padding: '2px', border: '1px solid var(--border-color)' }}>
            {(['all', 'Reviewed', 'Complete', 'Pending'] as const).map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => {
                  setStatusFilter(st);
                  setCurrentPage(1);
                }}
                style={{
                  background: statusFilter === st ? 'var(--bg-surface)' : 'transparent',
                  color: statusFilter === st ? '#ffffff' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {st === 'all' ? 'All Status' : st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="forensic-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="forensic-table">
          <thead>
            <tr>
              <th>Case ID</th>
              <th>Type</th>
              <th>Result</th>
              <th>Confidence</th>
              <th>Risk</th>
              <th>Date</th>
              <th>Status</th>
              <th style={{ textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {displayRows.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  No matching detection records found.
                </td>
              </tr>
            ) : (
              displayRows.map((row) => {
                const confPercent = row.confidence > 1 ? row.confidence : row.confidence * 100;
                return (
                  <tr
                    key={row.id}
                    onClick={() => navigate(`/investigations?scanId=${row.id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#ffffff' }}>
                      VM-{String(row.id).padStart(5, '0')}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', textTransform: 'capitalize' }}>
                        {getModalityIcon(row.media_type)}
                        <span>{row.media_type}</span>
                      </div>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          row.prediction === 'Fake'
                            ? 'badge-fake'
                            : row.prediction === 'Real'
                            ? 'badge-real'
                            : 'badge-uncertain'
                        }`}
                      >
                        {row.prediction}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{confPercent.toFixed(1)}%</td>
                    <td>
                      <span
                        style={{
                          fontWeight: 700,
                          fontSize: '0.8rem',
                          color:
                            row.risk === 'Critical'
                              ? 'var(--accent-red)'
                              : row.risk === 'High'
                              ? '#f87171'
                              : row.risk === 'Medium'
                              ? 'var(--accent-amber)'
                              : 'var(--accent-green)',
                        }}
                      >
                        {row.risk}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>{row.date}</td>
                    <td>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          color:
                            row.status === 'Reviewed'
                              ? 'var(--accent-green)'
                              : row.status === 'Complete'
                              ? 'var(--accent-blue)'
                              : 'var(--accent-amber)',
                          fontWeight: 600,
                        }}
                      >
                        {row.status}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <ExternalLink size={15} color="var(--text-muted)" />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Table Pagination Footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-dark)',
            fontSize: '0.8rem',
            color: 'var(--text-muted)',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <div>
            Showing {(safePage - 1) * pageSize + 1} to {Math.min(safePage * pageSize, filteredRows.length)} of {filteredRows.length} results
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              style={{ background: 'transparent', border: '1px solid var(--border-color)', color: safePage <= 1 ? '#475569' : 'var(--text-secondary)', padding: '4px 8px', borderRadius: '4px', cursor: safePage <= 1 ? 'not-allowed' : 'pointer' }}
            >
              <ChevronLeft size={14} />
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setCurrentPage(p)}
                style={{
                  backgroundColor: safePage === p ? 'var(--accent-blue)' : 'transparent',
                  color: safePage === p ? '#ffffff' : 'var(--text-secondary)',
                  border: safePage === p ? 'none' : '1px solid var(--border-color)',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  fontWeight: safePage === p ? 700 : 500,
                  cursor: 'pointer',
                }}
              >
                {p}
              </button>
            ))}

            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              style={{ background: 'transparent', border: '1px solid var(--border-color)', color: safePage >= totalPages ? '#475569' : 'var(--text-secondary)', padding: '4px 8px', borderRadius: '4px', cursor: safePage >= totalPages ? 'not-allowed' : 'pointer' }}
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
