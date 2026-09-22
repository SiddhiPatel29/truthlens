// Centralized Forensic Scan & Evidence State Manager
// Links: Analyze -> Investigation -> Report -> Evidence Vault -> History

export interface ForensicScanRecord {
  id: number;
  media_type: 'video' | 'audio' | 'image' | 'text';
  filename: string;
  filesize: string;
  created_at: string;
  sha256: string;
  preview_url?: string;
  text_content?: string;
  prediction: 'Fake' | 'Real' | 'Uncertain';
  confidence: number; // 0 to 100
  risk_level: 'Critical' | 'High' | 'Medium' | 'Low';
  status: 'Reviewed' | 'Complete' | 'Pending';
  raw_result?: any;
}

export interface VaultEvidenceAsset {
  id: string;
  name: string;
  size: string;
  type: 'Video' | 'Frame' | 'Heatmap' | 'Report' | 'Audio' | 'Text';
  date: string;
  hash: string;
  thumb: string;
  scan_id?: number;
}

const STORAGE_KEY_SCANS = 'veramedia_all_scans';
const STORAGE_KEY_VAULT = 'veramedia_vault_assets';
const STORAGE_KEY_ACTIVE = 'current_active_scan';

// Default initial demo scans
const DEFAULT_SCANS: ForensicScanRecord[] = [
  {
    id: 821,
    media_type: 'video',
    filename: 'deepfake_speech_00821.mp4',
    filesize: '24.2 MB',
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    preview_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=600&auto=format&fit=crop&q=80',
    prediction: 'Fake',
    confidence: 98.2,
    risk_level: 'Critical',
    status: 'Reviewed',
  },
  {
    id: 820,
    media_type: 'image',
    filename: 'portrait_photo_clean.jpg',
    filesize: '3.4 MB',
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
    sha256: '9f4c82b1d3e4a9d4e5f6789012345678abcdef0123456789abcdef0123456789',
    preview_url: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&auto=format&fit=crop&q=80',
    prediction: 'Real',
    confidence: 92.4,
    risk_level: 'Low',
    status: 'Complete',
  },
  {
    id: 819,
    media_type: 'audio',
    filename: 'cloned_voice_statement.wav',
    filesize: '1.8 MB',
    created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
    sha256: 'a71e89b2c01d4ef32a1567bc9812401f89bcdef123456789abcdef0123456789',
    preview_url: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=600&auto=format&fit=crop&q=80',
    prediction: 'Fake',
    confidence: 88.7,
    risk_level: 'High',
    status: 'Reviewed',
  },
  {
    id: 818,
    media_type: 'text',
    filename: 'ai_generated_press_release.txt',
    filesize: '14 KB',
    created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    sha256: 'b12e34d567f890a123c456e789012345678901234567890abcdef1234567890a',
    text_content: 'The rapid advancement of artificial intelligence has revolutionized the way we interact with technology across the modern enterprise.',
    prediction: 'Uncertain',
    confidence: 72.1,
    risk_level: 'Medium',
    status: 'Pending',
  },
];

// Default initial vault assets
const DEFAULT_VAULT: VaultEvidenceAsset[] = [
  {
    id: 'ast_01',
    name: 'deepfake_speech_00821.mp4',
    size: '24.2 MB',
    type: 'Video',
    date: 'Today',
    hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    thumb: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&auto=format&fit=crop&q=80',
    scan_id: 821,
  },
  {
    id: 'ast_02',
    name: 'extracted_frame_18.jpg',
    size: '1.8 MB',
    type: 'Frame',
    date: 'Today',
    hash: '9f4c82b1d3e4a9d4e5f6789012345678abcdef0123456789abcdef0123456789',
    thumb: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&auto=format&fit=crop&q=80',
    scan_id: 821,
  },
  {
    id: 'ast_03',
    name: 'forensic_heatmap_18.png',
    size: '2.4 MB',
    type: 'Heatmap',
    date: 'Today',
    hash: 'a71e89b2c01d4ef32a1567bc9812401f89bcdef123456789abcdef0123456789',
    thumb: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&auto=format&fit=crop&q=80',
    scan_id: 821,
  },
  {
    id: 'ast_04',
    name: 'forensic_dossier_VM-821.pdf',
    size: '2.8 MB',
    type: 'Report',
    date: 'Today',
    hash: 'b12e34d567f890a123c456e789012345678901234567890abcdef1234567890a',
    thumb: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&auto=format&fit=crop&q=80',
    scan_id: 821,
  },
];

export function getAllScans(): ForensicScanRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_SCANS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY_SCANS, JSON.stringify(DEFAULT_SCANS));
      return DEFAULT_SCANS;
    }
    return JSON.parse(raw);
  } catch {
    return DEFAULT_SCANS;
  }
}

export function getScanRecord(scanId: number | string): ForensicScanRecord | null {
  const all = getAllScans();
  const idNum = Number(scanId);
  const found = all.find((s) => s.id === idNum);
  if (found) return found;

  const active = getActiveScan();
  if (active && (active.id === idNum || String(active.id) === String(scanId))) {
    return active;
  }

  // Only return default if scanId was not provided or specifically matches default 821
  if (!scanId || String(scanId) === '821') {
    return all[0] || null;
  }

  return null;
}

export function getActiveScan(): ForensicScanRecord | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY_ACTIVE);
    return raw ? JSON.parse(raw) : getAllScans()[0] || null;
  } catch {
    return getAllScans()[0] || null;
  }
}

export function setActiveScan(scan: ForensicScanRecord): void {
  sessionStorage.setItem(STORAGE_KEY_ACTIVE, JSON.stringify(scan));
}

export function getAllVaultAssets(): VaultEvidenceAsset[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_VAULT);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY_VAULT, JSON.stringify(DEFAULT_VAULT));
      return DEFAULT_VAULT;
    }
    return JSON.parse(raw);
  } catch {
    return DEFAULT_VAULT;
  }
}

// Register a newly completed scan from Upload / Analyze
export function registerNewScan(
  modality: 'video' | 'audio' | 'image' | 'text',
  fileOrText: File | string,
  rawResult: any
): ForensicScanRecord {
  const isSynthetic =
    rawResult?.is_deepfake ??
    rawResult?.is_synthetic_audio ??
    rawResult?.is_ai_generated ??
    (rawResult?.prediction ? rawResult.prediction === 'Fake' : false);

  const rawConf =
    rawResult?.confidence_score ??
    rawResult?.ai_confidence_score ??
    rawResult?.confidence ??
    0;
  const normalizedConfidence = Math.min(99.9, rawConf > 1 ? rawConf : rawConf * 100);

  const riskLevel = isSynthetic
    ? normalizedConfidence > 85
      ? 'Critical'
      : 'High'
    : 'Low';

  const scanId = rawResult?.scan_id || Math.floor(822 + Math.random() * 100);

  let filename = '';
  let filesize = '';
  let previewUrl = '';
  let textContent = '';

  if (fileOrText instanceof File) {
    filename = fileOrText.name;
    const mb = fileOrText.size / (1024 * 1024);
    filesize = mb < 1 ? `${(fileOrText.size / 1024).toFixed(1)} KB` : `${mb.toFixed(2)} MB`;
    if (modality === 'image' || modality === 'video') {
      try {
        previewUrl = URL.createObjectURL(fileOrText);
      } catch {
        previewUrl = rawResult?.heatmap_preview || '';
      }
    }
  } else {
    filename = `text_passage_${scanId}.txt`;
    filesize = `${fileOrText.length} chars`;
    textContent = fileOrText;
  }

  // Generate simulated cryptographic SHA-256
  const sha256 = Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join('');

  const newScan: ForensicScanRecord = {
    id: scanId,
    media_type: modality,
    filename,
    filesize,
    created_at: new Date().toISOString(),
    sha256,
    preview_url: previewUrl || rawResult?.heatmap_preview || '',
    text_content: textContent,
    prediction: isSynthetic ? 'Fake' : 'Real',
    confidence: Number(normalizedConfidence.toFixed(1)),
    risk_level: riskLevel,
    status: 'Reviewed',
    raw_result: rawResult,
  };

  // 1. Set as currently active scan
  setActiveScan(newScan);

  // 2. Prepend to All Scans
  const scans = getAllScans();
  const updatedScans = [newScan, ...scans.filter((s) => s.id !== scanId)];
  localStorage.setItem(STORAGE_KEY_SCANS, JSON.stringify(updatedScans));

  // 3. Prepend newly generated evidence assets to Vault
  const vault = getAllVaultAssets();
  const newVaultAsset: VaultEvidenceAsset = {
    id: `ast_${scanId}_source`,
    name: filename,
    size: filesize,
    type: modality === 'video' ? 'Video' : modality === 'image' ? 'Frame' : modality === 'audio' ? 'Audio' : 'Text',
    date: 'Just now',
    hash: sha256,
    thumb:
      previewUrl ||
      (modality === 'image'
        ? 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&auto=format&fit=crop&q=80'
        : modality === 'video'
        ? 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&auto=format&fit=crop&q=80'
        : modality === 'audio'
        ? 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&auto=format&fit=crop&q=80'
        : 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&auto=format&fit=crop&q=80'),
    scan_id: scanId,
  };

  const updatedVault = [newVaultAsset, ...vault];
  localStorage.setItem(STORAGE_KEY_VAULT, JSON.stringify(updatedVault));

  return newScan;
}
