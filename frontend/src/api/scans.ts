import { request } from './client';
import { ApiResponse, ScanSummary } from '../types';

export async function getScans(): Promise<ApiResponse<ScanSummary[]>> {
  try {
    return await request<ScanSummary[]>('/api/scans', {
      method: 'GET',
    });
  } catch (err: any) {
    if (err?.errorCode === 'NETWORK_ERROR' || err?.message?.includes('Cannot connect')) {
      return {
        success: true,
        message: 'Loaded mock scans (Offline Demo Mode)',
        data: [
          {
            id: 101,
            media_type: 'video',
            filename: 'deepfake_speech_broadcast.mp4',
            status: 'COMPLETED',
            created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
            result: {
              id: 501,
              prediction: 'Fake',
              confidence: 96.4,
              risk_level: 'CRITICAL',
              result_data: { duration: 14.8, anomaly_peak: 0.94 },
            },
          },
          {
            id: 102,
            media_type: 'image',
            filename: 'politician_press_portrait.jpg',
            status: 'COMPLETED',
            created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
            result: {
              id: 502,
              prediction: 'Fake',
              confidence: 91.2,
              risk_level: 'HIGH',
              result_data: { manipulation: 'Diffusion blend' },
            },
          },
          {
            id: 103,
            media_type: 'audio',
            filename: 'executive_voicemail_leak.wav',
            status: 'COMPLETED',
            created_at: new Date(Date.now() - 3600000 * 9).toISOString(),
            result: {
              id: 503,
              prediction: 'Fake',
              confidence: 88.5,
              risk_level: 'HIGH',
              result_data: { lip_sync_offset_ms: 180 },
            },
          },
          {
            id: 104,
            media_type: 'text',
            filename: 'disinformation_press_release.txt',
            status: 'COMPLETED',
            created_at: new Date(Date.now() - 3600000 * 14).toISOString(),
            result: {
              id: 504,
              prediction: 'Fake',
              confidence: 94.8,
              risk_level: 'CRITICAL',
              result_data: { perplexity: 18.4 },
            },
          },
          {
            id: 105,
            media_type: 'video',
            filename: 'authentic_press_briefing.mp4',
            status: 'COMPLETED',
            created_at: new Date(Date.now() - 3600000 * 22).toISOString(),
            result: {
              id: 505,
              prediction: 'Real',
              confidence: 99.1,
              risk_level: 'LOW',
              result_data: { duration: 42.0 },
            },
          },
        ],
        error_code: null,
      };
    }
    throw err;
  }
}

export async function getScanById(scanId: number | string): Promise<ApiResponse<ScanSummary>> {
  try {
    return await request<ScanSummary>(`/api/scans/${scanId}`, {
      method: 'GET',
    });
  } catch (err: any) {
    if (err?.errorCode === 'NETWORK_ERROR' || err?.message?.includes('Cannot connect')) {
      return {
        success: true,
        message: 'Scan loaded (Offline Demo Mode)',
        data: {
          id: Number(scanId) || 101,
          media_type: 'video',
          filename: 'forensic_investigation_sample.mp4',
          status: 'COMPLETED',
          created_at: new Date().toISOString(),
          result: {
            id: 999,
            prediction: 'Fake',
            confidence: 94.2,
            risk_level: 'HIGH',
            result_data: {},
          },
        },
        error_code: null,
      };
    }
    throw err;
  }
}
