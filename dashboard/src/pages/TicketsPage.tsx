import React, { useState } from 'react';
import { TicketItem, MessageItem, api } from '../api';
import { User, Bot, AlertTriangle, X } from 'lucide-react';

interface TicketsPageProps {
  tickets: TicketItem[];
  loading: boolean;
}

export const TicketsPage: React.FC<TicketsPageProps> = ({ tickets, loading }) => {
  const [selectedTicket, setSelectedTicket] = useState<TicketItem | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  const handleSelectTicket = async (ticket: TicketItem) => {
    setSelectedTicket(ticket);
    setLoadingMessages(true);
    try {
      const msgs = await api.getTicketMessages(ticket.id);
      setMessages(msgs);
    } catch (e) {
      console.error('Failed to load ticket messages:', e);
    } finally {
      setLoadingMessages(false);
    }
  };

  const getStatusBadge = (status: TicketItem['status']) => {
    switch (status) {
      case 'answered':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800">
            Answered
          </span>
        );
      case 'escalated':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-800 flex items-center w-fit space-x-1">
            <AlertTriangle className="w-3 h-3 mr-1" /> Escalated
          </span>
        );
      case 'open':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">
            Open
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-800">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Support Tickets</h1>
        <p className="text-sm text-slate-500">
          Inbound customer threads, categorization, and conversation histories.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tickets List */}
        <div className={`bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm ${selectedTicket ? 'lg:col-span-1' : 'lg:col-span-3'}`}>
          <div className="divide-y divide-slate-100">
            {tickets.length === 0 ? (
              <div className="p-12 text-center text-slate-400">
                {loading ? 'Loading tickets...' : 'No tickets found.'}
              </div>
            ) : (
              tickets.map((t) => (
                <div
                  key={t.id}
                  onClick={() => handleSelectTicket(t)}
                  className={`p-4 hover:bg-slate-50 transition cursor-pointer ${
                    selectedTicket?.id === t.id ? 'bg-slate-50 border-l-4 border-emerald-600' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      {t.category}
                    </span>
                    {getStatusBadge(t.status)}
                  </div>
                  <h3 className="font-semibold text-slate-900 text-sm mt-1 truncate">
                    {t.subject || 'No Subject'}
                  </h3>
                  <div className="flex items-center justify-between text-xs text-slate-500 mt-2">
                    <span className="truncate max-w-[180px]">{t.customer}</span>
                    <span>{new Date(t.updated_at).toLocaleDateString()}</span>
                  </div>
                  {t.proposed_action && (
                    <div className="mt-2 text-[11px] font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded w-fit">
                      Action: {t.proposed_action}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Conversation Thread Detail */}
        {selectedTicket && (
          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl shadow-sm flex flex-col h-[700px] overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
              <div>
                <div className="flex items-center space-x-2">
                  <h2 className="font-bold text-slate-900 text-base">{selectedTicket.subject}</h2>
                  {getStatusBadge(selectedTicket.status)}
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Customer: <span className="text-slate-800 font-medium">{selectedTicket.customer}</span> • Thread ID: <span className="font-mono">{selectedTicket.thread_id}</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedTicket(null)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Messages Scroll View */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {loadingMessages ? (
                <div className="p-12 text-center text-slate-400">Loading conversation messages...</div>
              ) : messages.length === 0 ? (
                <div className="p-12 text-center text-slate-400">No message contents found in database.</div>
              ) : (
                messages.map((m) => {
                  const isIncoming = m.direction === 'incoming';
                  return (
                    <div
                      key={m.id}
                      className={`flex flex-col ${isIncoming ? 'items-start' : 'items-end'}`}
                    >
                      <div className="flex items-center space-x-1.5 mb-1 px-1">
                        {isIncoming ? (
                          <User className="w-3.5 h-3.5 text-slate-400" />
                        ) : (
                          <Bot className="w-3.5 h-3.5 text-emerald-600" />
                        )}
                        <span className="text-xs font-semibold text-slate-600">
                          {isIncoming ? m.sender : 'Harbor & Pine Support'}
                        </span>
                        <span className="text-[11px] text-slate-400 ml-1">
                          {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div
                        className={`max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                          isIncoming
                            ? 'bg-slate-100 text-slate-900 border border-slate-200'
                            : 'bg-emerald-50 text-emerald-950 border border-emerald-200'
                        }`}
                      >
                        {m.body}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
