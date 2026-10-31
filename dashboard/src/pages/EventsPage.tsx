import React from 'react';
import { EventItem } from '../api';
import { AlertCircle, CheckCircle2, Clock, RefreshCw } from 'lucide-react';

interface EventsPageProps {
  events: EventItem[];
  loading: boolean;
  onRefresh: () => void;
}

export const EventsPage: React.FC<EventsPageProps> = ({ events, loading, onRefresh }) => {
  const getStatusBadge = (status: EventItem['status']) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
            <CheckCircle2 className="w-3 h-3 mr-1" /> Completed
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> Processing
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            <AlertCircle className="w-3 h-3 mr-1" /> Failed
          </span>
        );
      case 'retrying':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
            <Clock className="w-3 h-3 mr-1" /> Retrying
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
            Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Processing Events</h1>
          <p className="text-sm text-slate-500">
            Audit trail of message processing cycles and background worker states.
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-2 text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 font-semibold text-xs uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3">Message ID</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Attempts</th>
                <th className="px-6 py-3">Decision / Outcome</th>
                <th className="px-6 py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                    No processing events recorded yet.
                  </td>
                </tr>
              ) : (
                events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-slate-700">
                      {ev.message_id}
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(ev.status)}</td>
                    <td className="px-6 py-4 text-slate-600">{ev.attempts}</td>
                    <td className="px-6 py-4">
                      {ev.result ? (
                        <div className="text-xs">
                          <span className="font-semibold text-slate-800 capitalize">
                            {ev.result.action || 'Unknown'}
                          </span>
                          {ev.result.section && (
                            <span className="text-slate-500 ml-1.5">
                              ({ev.result.section})
                            </span>
                          )}
                          {ev.result.proposed_action && (
                            <span className="ml-2 px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[11px]">
                              {ev.result.proposed_action}
                            </span>
                          )}
                        </div>
                      ) : ev.error ? (
                        <span className="text-xs text-red-600 font-mono">{ev.error}</span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {new Date(ev.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
