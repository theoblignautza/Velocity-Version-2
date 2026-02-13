export enum DeviceType {
  IOS = 'cisco_ios',
  IOS_XE = 'cisco_ios_xe',
  NX_OS = 'cisco_nxos',
}

export type ProtocolType = 'ssh' | 'telnet';

export interface BackupRequest {
  device_ip: string;
  username: string;
  password: string;
  device_type: DeviceType;
  protocol: ProtocolType;
}

export interface BackupResponse {
  status: 'success' | 'error';
  message?: string;
  device?: string;
  file?: string;
}

export interface DiscoveryDevice {
  ip: string;
  open_ports: number[];
  protocols: ProtocolType[];
}

export interface BackupFile {
  path: string;
  name: string;
  modified: string;
}

export interface RestoreRequest extends BackupRequest {
  backup_file: string;
}

export interface LogEvent {
  timestamp: string;
  level: string;
  message: string;
}

export type BackupStatus = 'idle' | 'loading' | 'success' | 'error';
