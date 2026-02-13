
import React, { useState } from 'react';
import { BackupForm } from './components/BackupForm';
import { StatusDisplay } from './components/StatusDisplay';
import { performBackup } from './services/backupService';
import type { BackupRequest, BackupResponse, BackupStatus } from './types';
import { ServerIcon } from './components/icons';

const App: React.FC = () => {
  const [status, setStatus] = useState<BackupStatus>('idle');
  const [response, setResponse] = useState<BackupResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleBackup = async (request: BackupRequest) => {
    setStatus('loading');
    setResponse(null);
    setError(null);
    try {
      const result = await performBackup(request);
      setResponse(result);
      setStatus('success');
    } catch (err: any) {
      setError(err.message || 'An unknown error occurred.');
      setResponse(err);
      setStatus('error');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200 flex flex-col items-center justify-center p-4 font-sans">
      <div className="w-full max-w-2xl mx-auto">
        <header className="text-center mb-8">
          <div className="flex items-center justify-center gap-4">
             <ServerIcon className="w-12 h-12 text-cyan-400" />
            <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
              Cisco Config Backup
            </h1>
          </div>
          <p className="text-slate-400 mt-2">A simple dashboard to trigger remote device configuration backups.</p>
        </header>

        <main>
          <BackupForm
            onSubmit={handleBackup}
            loading={status === 'loading'}
          />
          <div className="mt-8">
            <StatusDisplay status={status} response={response} error={error} />
          </div>
        </main>
        
        <footer className="text-center mt-12 text-slate-500 text-sm">
            <p>This frontend does not connect to devices directly. All operations are handled by a secure backend.</p>
        </footer>
      </div>
    </div>
  );
};

export default App;
   
