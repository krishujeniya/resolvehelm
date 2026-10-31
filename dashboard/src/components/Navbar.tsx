import React from 'react';
import { Mail, CheckCircle2, BookOpen, LogOut, RefreshCw } from 'lucide-react';

interface NavbarProps {
  currentTab: 'events' | 'tickets' | 'kb';
  setTab: (tab: 'events' | 'tickets' | 'kb') => void;
  onLogout: () => void;
  onPoll: () => void;
  isPolling: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  setTab,
  onLogout,
  onPoll,
  isPolling,
}) => {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold shadow-sm">
            RH
          </div>
          <div>
            <span className="font-bold text-lg tracking-tight text-slate-900">ResolveHelm</span>
            <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
              Harbor & Pine
            </span>
          </div>
        </div>

        <nav className="flex space-x-1 sm:space-x-2">
          <button
            onClick={() => setTab('events')}
            className={`px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2 transition-colors ${
              currentTab === 'events'
                ? 'bg-slate-100 text-slate-900 font-semibold'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Events</span>
          </button>
          <button
            onClick={() => setTab('tickets')}
            className={`px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2 transition-colors ${
              currentTab === 'tickets'
                ? 'bg-slate-100 text-slate-900 font-semibold'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <Mail className="w-4 h-4" />
            <span>Tickets</span>
          </button>
          <button
            onClick={() => setTab('kb')}
            className={`px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2 transition-colors ${
              currentTab === 'kb'
                ? 'bg-slate-100 text-slate-900 font-semibold'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Knowledge Base</span>
          </button>
        </nav>

        <div className="flex items-center space-x-2">
          <button
            onClick={onPoll}
            disabled={isPolling}
            className="px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white flex items-center space-x-1.5 shadow-sm transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isPolling ? 'animate-spin' : ''}`} />
            <span>{isPolling ? 'Checking...' : 'Check Inbox'}</span>
          </button>

          <button
            onClick={onLogout}
            title="Log out"
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-md transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
