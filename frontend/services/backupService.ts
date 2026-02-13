import type {
  BackupFile,
  BackupRequest,
  BackupResponse,
  DiscoveryDevice,
  LogEvent,
  RestoreRequest,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';
const buildUrl = (path: string) => `${API_BASE_URL}${path}`;

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message = errorBody?.detail || errorBody?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return response.json();
}

export const performBackup = async (request: BackupRequest): Promise<BackupResponse> => {
  const response = await fetch(buildUrl('/api/backup-config'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return parseJson<BackupResponse>(response);
};

export const discoverSwitches = async (subnet: string): Promise<DiscoveryDevice[]> => {
  const response = await fetch(buildUrl('/api/discover-switches'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subnet }),
  });
  const data = await parseJson<{ devices: DiscoveryDevice[] }>(response);
  return data.devices;
};

export const listBackups = async (): Promise<BackupFile[]> => {
  const response = await fetch(buildUrl('/api/backups'));
  const data = await parseJson<{ files: BackupFile[] }>(response);
  return data.files;
};

export const readBackupContent = async (path: string): Promise<string> => {
  const response = await fetch(buildUrl(`/api/backups/content?path=${encodeURIComponent(path)}`));
  const data = await parseJson<{ content: string }>(response);
  return data.content;
};

export const restoreConfig = async (request: RestoreRequest): Promise<BackupResponse> => {
  const response = await fetch(buildUrl('/api/restore-config'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return parseJson<BackupResponse>(response);
};

export const createLogSocket = (onEvent: (event: LogEvent) => void): WebSocket => {
  const base = API_BASE_URL || window.location.origin;
  const wsUrl = `${base.replace(/^http/, 'ws')}/ws/logs`;
  const socket = new WebSocket(wsUrl);
  socket.onmessage = (event) => {
    try {
      onEvent(JSON.parse(event.data) as LogEvent);
    } catch {
      onEvent({ timestamp: new Date().toISOString(), level: 'error', message: 'Invalid log event payload' });
    }
  };
  return socket;
};
