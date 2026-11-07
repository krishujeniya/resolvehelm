import React, { useState, useEffect } from 'react';
import { TicketItem, MessageItem, TicketNote, api } from '../api';
import {
  User,
  Bot,
  AlertTriangle,
  CheckCircle2,
  X,
  Send,
  FileText,
  MessageSquare,
  Plus,
  RotateCcw,
  Check
} from 'lucide-react';

interface TicketsPageProps {
  tickets: TicketItem[];
  loading: boolean;
  onRefresh?: () => void;
}

export const TicketsPage: React.FC<TicketsPageProps> = ({ tickets, loading, onRefresh }) => {
  const [selectedTicket, setSelectedTicket] = useState<TicketItem | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [notes, setNotes] = useState<TicketNote[]>([]);
  const [activeTab, setActiveTab] = useState<'conversation' | 'notes'>('conversation');
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Form states
  const [replyText, setReplyText] = useState('');
  const [sendingReply, setSendingReply] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [addingNote, setAddingNote] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (selectedTicket) {
      loadTicketDetails(selectedTicket.id);
    }
  }, [selectedTicket?.id]);

  const loadTicketDetails = async (ticketId: string) => {
    setLoadingDetails(true);
    try {
      const [msgs, nts] = await Promise.all([
        api.getTicketMessages(ticketId).catch(() => []),
        api.getTicketNotes(ticketId).catch(() => []),
      ]);
      setMessages(msgs);
      setNotes(nts);
    } catch (e) {
      console.error('Failed to load ticket details:', e);
    } finally {
      setLoadingDetails(false);
    }
  };

  const showNotification = (type: 'success' | 'error', text: string) => {
    setFeedbackMsg({ type, text });
    setTimeout(() => setFeedbackMsg(null), 3500);
  };

  const handleSelectTicket = (ticket: TicketItem) => {
    setSelectedTicket(ticket);
    setReplyText('');
    setNoteText('');
    setActiveTab('conversation');
  };

  const handleStatusChange = async (newStatus: 'open' | 'answered' | 'escalated' | 'closed' | 'resolved') => {
    if (!selectedTicket) return;
    setUpdatingStatus(true);
    try {
      const res = await api.updateTicket(selectedTicket.id, { status: newStatus });
      setSelectedTicket(res.ticket);
      showNotification('success', `Ticket status updated to ${newStatus}`);
      if (onRefresh) onRefresh();
    } catch (e: any) {
      showNotification('error', e.message || 'Failed to update status');
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleSendReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !replyText.trim() || sendingReply) return;

    setSendingReply(true);
    try {
      await api.sendManualReply(selectedTicket.id, replyText.trim());
      setReplyText('');
      showNotification('success', 'Manual reply sent successfully');
      await loadTicketDetails(selectedTicket.id);
      if (onRefresh) onRefresh();
      // Update local ticket status to answered
      setSelectedTicket((prev) => (prev ? { ...prev, status: 'answered' } : null));
    } catch (e: any) {
      showNotification('error', e.message || 'Failed to send reply');
    } finally {
      setSendingReply(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !noteText.trim() || addingNote) return;

    setAddingNote(true);
    try {
      await api.addTicketNote(selectedTicket.id, noteText.trim());
      setNoteText('');
      showNotification('success', 'Internal note added');
      const updatedNotes = await api.getTicketNotes(selectedTicket.id);
      setNotes(updatedNotes);
    } catch (e: any) {
      showNotification('error', e.message || 'Failed to add note');
    } finally {
      setAddingNote(false);
    }
  };

  const getStatusBadge = (status: TicketItem['status']) => {
    switch (status) {
      case 'resolved':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 flex items-center space-x-1">
            <Check className="w-3 h-3 mr-1" /> Resolved
          </span>
        );
      case 'answered':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-teal-100 text-teal-800">
            Answered
          </span>
        );
      case 'escalated':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-100 text-rose-800 flex items-center w-fit space-x-1">
            <AlertTriangle className="w-3 h-3 mr-1" /> Escalated
          </span>
        );
      case 'open':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">
            Open
          </span>
        );
      case 'closed':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-200 text-slate-800">
            Closed
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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Support Tickets & Operations</h1>
          <p className="text-sm text-slate-500">
            Inbound customer threads, human escalation triage, manual replies, and internal notes.
          </p>
        </div>
        {feedbackMsg && (
          <div
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-all duration-200 ${
              feedbackMsg.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}
          >
            {feedbackMsg.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-600" />
            )}
            <span>{feedbackMsg.text}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tickets List */}
        <div
          className={`bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm ${
            selectedTicket ? 'lg:col-span-1' : 'lg:col-span-3'
          }`}
        >
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
                  {t.assigned_to && (
                    <div className="mt-1 text-[11px] text-slate-500">
                      Assigned: <span className="font-medium text-slate-700">{t.assigned_to}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Conversation Thread & Operations Panel */}
        {selectedTicket && (
          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl shadow-sm flex flex-col h-[750px] overflow-hidden">
            {/* Header with Ticket Details & Actions */}
            <div className="p-4 border-b border-slate-200 bg-slate-50/50">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <h2 className="font-bold text-slate-900 text-base">{selectedTicket.subject}</h2>
                    {getStatusBadge(selectedTicket.status)}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Customer: <span className="text-slate-800 font-medium">{selectedTicket.customer}</span> • Thread ID:{' '}
                    <span className="font-mono">{selectedTicket.thread_id}</span>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedTicket(null)}
                  className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition active:scale-[0.98]"
                  title="Close Ticket View"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Status Action Buttons */}
              <div className="mt-3 pt-3 border-t border-slate-200/80 flex flex-wrap items-center gap-2">
                <span className="text-xs font-medium text-slate-600 mr-1">Status:</span>
                {selectedTicket.status !== 'resolved' && (
                  <button
                    disabled={updatingStatus}
                    onClick={() => handleStatusChange('resolved')}
                    className="px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition active:scale-[0.98] disabled:opacity-50 flex items-center space-x-1"
                  >
                    <Check className="w-3.5 h-3.5 mr-1" /> Mark Resolved
                  </button>
                )}
                {selectedTicket.status !== 'escalated' && (
                  <button
                    disabled={updatingStatus}
                    onClick={() => handleStatusChange('escalated')}
                    className="px-2.5 py-1 text-xs font-semibold rounded-md bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 transition active:scale-[0.98] disabled:opacity-50 flex items-center space-x-1"
                  >
                    <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Escalate
                  </button>
                )}
                {selectedTicket.status !== 'open' && (
                  <button
                    disabled={updatingStatus}
                    onClick={() => handleStatusChange('open')}
                    className="px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition active:scale-[0.98] disabled:opacity-50 flex items-center space-x-1"
                  >
                    <RotateCcw className="w-3.5 h-3.5 mr-1" /> Re-open
                  </button>
                )}
                {selectedTicket.status !== 'closed' && (
                  <button
                    disabled={updatingStatus}
                    onClick={() => handleStatusChange('closed')}
                    className="px-2.5 py-1 text-xs font-semibold rounded-md bg-slate-100 text-slate-700 border border-slate-200 hover:bg-slate-200 transition active:scale-[0.98] disabled:opacity-50"
                  >
                    Close
                  </button>
                )}

                {/* Sub-Tabs: Conversation vs Internal Notes */}
                <div className="ml-auto flex items-center bg-slate-200/70 p-0.5 rounded-lg text-xs font-medium">
                  <button
                    onClick={() => setActiveTab('conversation')}
                    className={`px-3 py-1 rounded-md transition duration-150 flex items-center space-x-1 ${
                      activeTab === 'conversation'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5 mr-1" />
                    <span>Conversation ({messages.length})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('notes')}
                    className={`px-3 py-1 rounded-md transition duration-150 flex items-center space-x-1 ${
                      activeTab === 'notes'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5 mr-1" />
                    <span>Notes ({notes.length})</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Main Content Area */}
            {activeTab === 'conversation' ? (
              <div className="flex-1 flex flex-col min-h-0">
                {/* Messages Scroll View */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {loadingDetails ? (
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

                {/* Manual Reply Composer */}
                <form
                  onSubmit={handleSendReply}
                  className="p-3 border-t border-slate-200 bg-slate-50/50 flex flex-col gap-2"
                >
                  <textarea
                    rows={3}
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Compose manual reply to customer... (records outgoing email and marks ticket Answered)"
                    className="w-full text-sm p-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none bg-white placeholder-slate-400"
                  />
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">
                      Operator manual reply mode • Grounded by team standards
                    </span>
                    <button
                      type="submit"
                      disabled={sendingReply || !replyText.trim()}
                      className="px-4 py-2 bg-emerald-600 text-white text-xs font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition active:scale-[0.98] flex items-center space-x-1.5"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{sendingReply ? 'Sending...' : 'Send Reply'}</span>
                    </button>
                  </div>
                </form>
              </div>
            ) : (
              /* Internal Operator Notes Tab */
              <div className="flex-1 flex flex-col min-h-0">
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {loadingDetails ? (
                    <div className="p-12 text-center text-slate-400">Loading notes...</div>
                  ) : notes.length === 0 ? (
                    <div className="p-12 text-center text-slate-400">
                      No internal notes recorded yet for this ticket.
                    </div>
                  ) : (
                    notes.map((n) => (
                      <div
                        key={n.id}
                        className="bg-amber-50/60 border border-amber-200/70 rounded-lg p-3 text-sm text-slate-800"
                      >
                        <div className="flex items-center justify-between text-xs text-amber-900/80 mb-1 font-medium">
                          <span>Operator: {n.author}</span>
                          <span>{new Date(n.created_at).toLocaleString()}</span>
                        </div>
                        <p className="whitespace-pre-wrap">{n.note}</p>
                      </div>
                    ))
                  )}
                </div>

                {/* Add Note Form */}
                <form
                  onSubmit={handleAddNote}
                  className="p-3 border-t border-slate-200 bg-slate-50/50 flex flex-col gap-2"
                >
                  <textarea
                    rows={2}
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Add an internal note (visible only to support operators)..."
                    className="w-full text-sm p-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none bg-white placeholder-slate-400"
                  />
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">
                      Private support team memo • Never sent to customer
                    </span>
                    <button
                      type="submit"
                      disabled={addingNote || !noteText.trim()}
                      className="px-4 py-2 bg-amber-600 text-white text-xs font-semibold rounded-lg hover:bg-amber-700 disabled:opacity-50 transition active:scale-[0.98] flex items-center space-x-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>{addingNote ? 'Adding...' : 'Add Note'}</span>
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
