import React, { useState } from 'react';
import { Lock, ShieldAlert, Server } from 'lucide-react';
import { api } from '../api';

interface LoginModalProps {
  onSuccess: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onSuccess }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [apiUrl, setApiUrl] = useState(api.getBaseUrl());
  const [showConfig, setShowConfig] = useState(
    !api.getBaseUrl() &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1'
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (apiUrl) {
        api.setBaseUrl(apiUrl);
      }
      api.setCredentials(username, password);
      await api.verifyAuth();
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Invalid credentials or unreachable backend server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 sm:p-8">
        <div className="w-12 h-12 bg-emerald-50 rounded-lg flex items-center justify-center text-emerald-600 mb-4 mx-auto">
          <Lock className="w-6 h-6" />
        </div>

        <h2 className="text-xl font-bold text-center text-slate-900">Sign in to ResolveHelm</h2>
        <p className="text-sm text-center text-slate-500 mt-1">
          Support Automation & Policy Administration
        </p>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start space-x-2 text-red-700 text-sm">
            <ShieldAlert className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
              placeholder="admin"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
              placeholder="••••••••••••"
            />
          </div>

          <div className="pt-1">
            <button
              type="button"
              onClick={() => setShowConfig(!showConfig)}
              className="text-xs text-slate-500 hover:text-slate-800 flex items-center space-x-1.5 transition-colors"
            >
              <Server className="w-3.5 h-3.5" />
              <span>{showConfig ? 'Hide Backend Server URL' : 'Configure Backend Server URL'}</span>
            </button>
            {showConfig && (
              <div className="mt-2 p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  API Base URL
                </label>
                <input
                  type="url"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white text-xs font-mono focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  placeholder="https://your-backend.vercel.app"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Enter your Vercel backend deployment URL (e.g. https://xyz.vercel.app).
                </p>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg shadow-sm transition disabled:opacity-50 text-sm"
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};
