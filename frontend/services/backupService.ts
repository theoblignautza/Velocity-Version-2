
import type { BackupRequest, BackupResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

export const performBackup = async (request: BackupRequest): Promise<BackupResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/backup-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      const message =
        errorBody?.detail ||
        errorBody?.message ||
        `Backup failed with status ${response.status}.`;
      throw { status: 'error', message, device: request.device_ip };
    }

    return response.json();
  } catch (error: any) {
    if (error?.status === 'error') {
      throw error;
    }
    throw {
      status: 'error',
      message: error?.message || 'Unable to reach the backup service.',
      device: request.device_ip,
    };
  }
};
   
