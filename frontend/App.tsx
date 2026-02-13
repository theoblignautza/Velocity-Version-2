import React, { useEffect, useMemo, useState } from 'react';
import { DEVICE_TYPE_OPTIONS } from './constants';
import {
  createLogSocket,
  discoverSwitches,
  listBackups,
  performBackup,
  readBackupContent,
  restoreConfig,
} from './services/backupService';
import type { BackupFile, BackupResponse, DeviceType, DiscoveryDevice, LogEvent, ProtocolType } from './types';

const initialDevice = '10.0.0.5';

const App: React.FC = () => {
  const [deviceIp, setDeviceIp] = useState(initialDevice);
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('secret');
  const [deviceType, setDeviceType] = useState<DeviceType>(DEVICE_TYPE_OPTIONS[0].value);
  const [protocol, setProtocol] = useState<ProtocolType>('ssh');
  const [subnet, setSubnet] = useState('192.168.1.0/24');

  const [status, setStatus] = useState<string>('idle');
  const [message, setMessage] = useState<string>('');
  const [discoveries, setDiscoveries] = useState<DiscoveryDevice[]>([]);
  const [backupFiles, setBackupFiles] = useState<BackupFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [selectedContent, setSelectedContent] = useState<string>('Select a backup file to view content');
  const [logs, setLogs] = useState<LogEvent[]>([]);

  const sortedLogs = useMemo(() => logs.slice(-120), [logs]);

  useEffect(() => {
    const socket = createLogSocket((event) => {
      setLogs((prev) => [...prev, event]);
    });
    return () => socket.close();
  }, []);

  const refreshBackups = async () => {
    const files = await listBackups();
    setBackupFiles(files);
    if (files.length > 0 && !selectedFile) {
      setSelectedFile(files[0].path);
    }
  };

  useEffect(() => {
    refreshBackups().catch((error) => setMessage(error.message));
  }, []);

  const handleBackup = async () => {
    setStatus('loading');
    setMessage('Starting backup...');
    try {
      const response: BackupResponse = await performBackup({
        device_ip: deviceIp,
        username,
        password,
        device_type: deviceType,
        protocol,
      });
      setStatus('success');
      setMessage(`Backup complete for ${response.device}. File: ${response.file}`);
      await refreshBackups();
    } catch (error: any) {
      setStatus('error');
      setMessage(error.message || 'Backup failed');
    }
  };

  const handleDiscover = async () => {
    setStatus('loading');
    setMessage('Discovering switches...');
    try {
      const devices = await discoverSwitches(subnet);
      setDiscoveries(devices);
      setStatus('success');
      setMessage(`Discovery complete. Found ${devices.length} candidate devices.`);
    } catch (error: any) {
      setStatus('error');
      setMessage(error.message || 'Discovery failed');
    }
  };

  const handleViewFile = async () => {
    if (!selectedFile) return;
    try {
      setSelectedContent(await readBackupContent(selectedFile));
    } catch (error: any) {
      setSelectedContent(error.message || 'Unable to load backup file.');
    }
  };

  const handleRestore = async () => {
    if (!selectedFile) {
      setMessage('Choose a backup file before restoring.');
      return;
    }
    setStatus('loading');
    setMessage(`Restoring ${selectedFile} to ${deviceIp}...`);
    try {
      await restoreConfig({
        device_ip: deviceIp,
        username,
        password,
        device_type: deviceType,
        protocol,
        backup_file: selectedFile,
      });
      setStatus('success');
      setMessage('Restore completed successfully.');
    } catch (error: any) {
      setStatus('error');
      setMessage(error.message || 'Restore failed');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 p-4 font-sans">
      <div className="max-w-6xl mx-auto grid grid-cols-1 xl:grid-cols-3 gap-6">
        <section className="xl:col-span-2 bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-4">
          <h1 className="text-2xl font-bold text-white">Cisco Config Backup Dashboard</h1>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <input className="input" value={deviceIp} onChange={(e) => setDeviceIp(e.target.value)} placeholder="Device IP" />
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
            <select className="input" value={protocol} onChange={(e) => setProtocol(e.target.value as ProtocolType)}>
              <option value="ssh">SSH</option>
              <option value="telnet">Telnet</option>
            </select>
            <select className="input" value={deviceType} onChange={(e) => setDeviceType(e.target.value as DeviceType)}>
              {DEVICE_TYPE_OPTIONS.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
            <button className="btn" onClick={handleBackup}>Run Backup</button>
          </div>

          <div className="border-t border-slate-700 pt-4">
            <h2 className="font-semibold mb-2">Discover Switches</h2>
            <div className="flex gap-2">
              <input className="input flex-1" value={subnet} onChange={(e) => setSubnet(e.target.value)} placeholder="192.168.1.0/24" />
              <button className="btn" onClick={handleDiscover}>Discover</button>
            </div>
            <ul className="mt-3 space-y-2 max-h-48 overflow-auto text-sm">
              {discoveries.map((device) => (
                <li key={device.ip} className="bg-slate-900/50 px-3 py-2 rounded">
                  {device.ip} — ports: {device.open_ports.join(', ')} ({device.protocols.join(', ')})
                </li>
              ))}
            </ul>
          </div>

          <p className={`text-sm ${status === 'error' ? 'text-red-400' : 'text-cyan-300'}`}>{message}</p>
        </section>

        <section className="bg-slate-800/60 border border-slate-700 rounded-xl p-6">
          <h2 className="font-semibold mb-2">Live Logs</h2>
          <div className="bg-black/60 rounded p-3 h-[420px] overflow-auto text-xs font-mono space-y-1">
            {sortedLogs.map((entry, index) => (
              <div key={`${entry.timestamp}-${index}`} className={entry.level === 'error' ? 'text-red-300' : 'text-green-300'}>
                [{new Date(entry.timestamp).toLocaleTimeString()}] {entry.message}
              </div>
            ))}
          </div>
        </section>

        <section className="xl:col-span-3 bg-slate-800/60 border border-slate-700 rounded-xl p-6">
          <div className="flex flex-wrap gap-2 items-center">
            <h2 className="font-semibold mr-auto">Backed-up Config Files</h2>
            <button className="btn" onClick={refreshBackups}>Refresh Files</button>
            <button className="btn bg-amber-600 hover:bg-amber-500" onClick={handleRestore}>Restore Selected</button>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mt-3">
            <div className="bg-slate-900/50 rounded p-2 max-h-72 overflow-auto text-sm">
              {backupFiles.map((file) => (
                <button
                  key={file.path}
                  onClick={() => setSelectedFile(file.path)}
                  className={`block w-full text-left px-2 py-1 rounded ${selectedFile === file.path ? 'bg-cyan-700' : 'hover:bg-slate-700'}`}
                >
                  {file.path}
                </button>
              ))}
            </div>
            <div className="lg:col-span-2">
              <div className="flex gap-2 mb-2">
                <button className="btn" onClick={handleViewFile}>View Content</button>
                <span className="text-xs text-slate-400 break-all self-center">{selectedFile}</span>
              </div>
              <pre className="bg-black/60 rounded p-3 h-72 overflow-auto text-xs whitespace-pre-wrap">{selectedContent}</pre>
            </div>
          </div>
        </section>
      </div>
      <style>{`.input{background:rgba(15,23,42,.75);border:1px solid rgb(71 85 105);border-radius:.375rem;padding:.5rem .75rem;color:#e2e8f0}.btn{background:#0891b2;color:white;padding:.5rem .75rem;border-radius:.375rem;font-weight:600}.btn:hover{background:#06b6d4}`}</style>
    </div>
  );
};

export default App;
