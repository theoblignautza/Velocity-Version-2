
import React, { useState } from 'react';
import { DeviceType, type BackupRequest } from '../types';
import { DEVICE_TYPE_OPTIONS } from '../constants';
import { SpinnerIcon } from './icons';

interface BackupFormProps {
  onSubmit: (request: BackupRequest) => void;
  loading: boolean;
}

export const BackupForm: React.FC<BackupFormProps> = ({ onSubmit, loading }) => {
  const [deviceIp, setDeviceIp] = useState('10.0.0.5');
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('secret');
  const [deviceType, setDeviceType] = useState<DeviceType>(DeviceType.IOS);
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!deviceIp || !username || !password) {
      setError('All fields except Device Type are required.');
      return;
    }
    setError('');
    onSubmit({
      device_ip: deviceIp,
      username,
      password,
      device_type: deviceType,
    });
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6 md:p-8 shadow-2xl shadow-slate-900/50">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="device-ip" className="block text-sm font-medium text-slate-300 mb-1">Device IP / Hostname</label>
          <input
            id="device-ip"
            type="text"
            value={deviceIp}
            onChange={(e) => setDeviceIp(e.target.value)}
            className="w-full bg-slate-900/50 border border-slate-600 rounded-md px-3 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500"
            placeholder="e.g., 192.168.1.1"
            disabled={loading}
          />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-slate-300 mb-1">SSH Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-600 rounded-md px-3 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500"
              placeholder="e.g., admin"
              disabled={loading}
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1">SSH Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-600 rounded-md px-3 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500"
              placeholder="••••••••"
              disabled={loading}
            />
          </div>
        </div>
        <div>
          <label htmlFor="device-type" className="block text-sm font-medium text-slate-300 mb-1">Device Type</label>
          <select
            id="device-type"
            value={deviceType}
            onChange={(e) => setDeviceType(e.target.value as DeviceType)}
            className="w-full bg-slate-900/50 border border-slate-600 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500"
            disabled={loading}
          >
            {DEVICE_TYPE_OPTIONS.map(option => (
              <option key={option.value} value={option.value} className="bg-slate-800 text-white">
                {option.label}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div>
          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-bold py-3 px-4 rounded-md transition-all duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-800 focus:ring-cyan-500"
          >
            {loading ? (
              <>
                <SpinnerIcon className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" />
                Backing up...
              </>
            ) : (
              'Backup Config'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
   