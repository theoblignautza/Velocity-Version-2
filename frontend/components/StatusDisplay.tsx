
import React from 'react';
import type { BackupResponse, BackupStatus } from '../types';
import { CheckCircleIcon, XCircleIcon, FileIcon, SpinnerIcon } from './icons';

interface StatusDisplayProps {
  status: BackupStatus;
  response: BackupResponse | null;
  error: string | null;
}

export const StatusDisplay: React.FC<StatusDisplayProps> = ({ status, response, error }) => {
  if (status === 'idle') {
    return null;
  }

  if (status === 'loading') {
    return (
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 text-center animate-pulse">
        <div className="flex items-center justify-center text-slate-400">
          <SpinnerIcon className="animate-spin h-6 w-6 mr-3" />
          <p className="font-medium">Contacting backend and connecting to device...</p>
        </div>
      </div>
    );
  }

  if (status === 'success' && response) {
    return (
      <div className="bg-green-900/30 border border-green-500/50 rounded-xl p-6 shadow-lg">
        <div className="flex items-start">
          <CheckCircleIcon className="h-7 w-7 text-green-400 mr-4 flex-shrink-0" />
          <div>
            <h3 className="text-lg font-bold text-green-300">Backup Successful</h3>
            <p className="text-green-200/80 mt-1">Configuration for device <span className="font-mono bg-green-900/50 px-1 py-0.5 rounded">{response.device}</span> has been saved on the server.</p>
            <div className="mt-4 bg-slate-800/50 p-3 rounded-md flex items-center text-sm">
                <FileIcon className="h-5 w-5 text-slate-400 mr-3 flex-shrink-0" />
                <span className="text-slate-300 mr-2">File saved as:</span>
                <span className="font-mono text-cyan-400">{response.file}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  if (status === 'error') {
     return (
      <div className="bg-red-900/30 border border-red-500/50 rounded-xl p-6 shadow-lg">
        <div className="flex items-start">
          <XCircleIcon className="h-7 w-7 text-red-400 mr-4 flex-shrink-0" />
          <div>
            <h3 className="text-lg font-bold text-red-300">Backup Failed</h3>
            {response?.device && <p className="text-red-200/80 mt-1">An error occurred for device <span className="font-mono bg-red-900/50 px-1 py-0.5 rounded">{response.device}</span>.</p>}
            <p className="mt-2 text-red-200 bg-slate-800/50 p-3 rounded-md font-mono text-sm">{error || 'Unknown error'}</p>
          </div>
        </div>
      </div>
    );
  }

  return null;
};
   