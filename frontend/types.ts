
export enum DeviceType {
  IOS = 'cisco_ios',
  IOS_XE = 'cisco_ios_xe',
  NX_OS = 'cisco_nxos',
}

export interface BackupRequest {
  device_ip: string;
  username: string;
  password: string;
  device_type: DeviceType;
}

export interface BackupResponse {
  status: 'success' | 'error';
  message?: string;
  device?: string;
  file?: string;
}

export type BackupStatus = 'idle' | 'loading' | 'success' | 'error';
   
