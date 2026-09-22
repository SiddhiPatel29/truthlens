// Standard API Response Envelope
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T | null;
  error_code: string | null;
}

// Authenticated User Profile
export interface UserProfile {
  user_id: number;
  name: string;
  email: string;
  role?: string;
}

// Authentication Token Response
export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// Forensic Detection Common & Modality-Specific Types
export interface ImageDetectionResult {
  scan_id?: number;
  is_deepfake: boolean;
  confidence_score: number;
  manipulation_type: string;
  image_dimensions: { width: number; height: number };
  heatmap_preview: string; // Base64 Data URL
}

export interface VideoDetectionResult {
  scan_id?: number;
  is_deepfake: boolean;
  confidence_score: number;
  metrics: {
    duration_seconds: number;
    total_frames_analyzed: number;
    temporal_instability: number;
    peak_frame_anomaly: number;
  };
  keyframe_heatmap_preview?: string | null;
}

export interface AudioLipSyncDiscrepancy {
  start_timestamp: string;
  end_timestamp: string;
  measured_offset_ms: number;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  description: string;
}

export interface AudioDetectionResult {
  scan_id?: number;
  is_synthetic_audio: boolean;
  confidence_score: number;
  metrics: {
    duration_seconds: number;
    sample_rate_hz: number;
    zero_crossing_rate: number;
    energy_variance: number;
  };
  lip_sync_discrepancies: AudioLipSyncDiscrepancy[];
}

export interface TextSentenceBreakdown {
  sentence: string;
  word_count: number;
  suspicious: boolean;
}

export interface TextDetectionResult {
  scan_id?: number;
  is_ai_generated: boolean;
  ai_confidence_score: number;
  metrics: {
    total_sentences: number;
    total_words: number;
    burstiness_index: number;
    lexical_diversity: number;
  };
  sentence_breakdown: TextSentenceBreakdown[];
}

// Scan Record for History & Vault
export interface ScanSummary {
  id: number;
  user_id?: number;
  media_type: 'video' | 'audio' | 'image' | 'text';
  filename?: string | null;
  status: string;
  created_at: string;
  completed_at?: string | null;
  result?: {
    id: number;
    prediction: string;
    confidence: number;
    risk_level: string;
    result_data: any;
  };
}

// Abuse Report Dispatch
export interface AbuseDossierRequest {
  platform: 'youtube' | 'x' | 'meta' | 'custom';
  target_url: string;
  category: string;
  confidence_score: number;
  analyst_notes: string;
  scan_id?: number;
}

export interface AbuseDossierResponse {
  report_id: string;
  status: string;
  dispatch_timestamp: string;
  platform_destination: {
    platform: string;
    channel: string;
    target_url: string;
  };
  forensic_evidence: {
    category: string;
    confidence_score: number;
    sha256_fingerprint: string;
    analyst_notes: string;
    standards_compliance: string[];
  };
  dispatch_receipt: {
    acknowledgment_code: string;
    estimated_review_hours: number;
  };
}

// Health Check Response
export interface HealthStatus {
  service: string;
  status: string;
  version: string;
  supported_modalities: string[];
}
