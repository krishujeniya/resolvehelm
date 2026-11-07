import React, { useState } from 'react';
import { X, Sparkles, Send, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';
import { api } from '../api';

interface SimulateModalProps {
  onClose: () => void;
  onSuccess: (ticketId: string) => void;
}

const PRESETS = [
  {
    label: 'Slow leak after valve check (Warranty Escalation)',
    name: 'Mia Jansen',
    email: 'mia@example.com',
    subject: 'Still losing air',
    body: 'I completed the valve check with soapy water and tightened the valve core, but it is still losing air.',
  },
  {
    label: 'Missing screws with order (Hardware Kit Escalation)',
    name: 'Sarah Connor',
    email: 'sarah@example.com',
    subject: 'No screws in the box',
    body: 'My HP-C4 cube unit arrived without screws. Order 112-7711223-4455667.',
  },
  {
    label: 'Back panel assembly question (Auto-Reply)',
    name: 'Chris Pratt',
    email: 'chris@example.com',
    subject: 'Back panel question',
    body: 'Which side of the back panel should face inside the shelf?',
  },
  {
    label: 'Order status inquiry (Shipping Escalation)',
    name: 'Tom Hanks',
    email: 'tom@example.com',
    subject: 'Where is my order?',
    body: 'Where is my order 112-9988776-5544332? It has been over a week.',
  },
];

export const SimulateModal: React.FC<SimulateModalProps> = ({ onClose, onSuccess }) => {
  const [selectedPreset, setSelectedPreset] = useState(0);
  const [name, setName] = useState(PRESETS[0].name);
  const [email, setEmail] = useState(PRESETS[0].email);
  const [subject, setSubject] = useState(PRESETS[0].subject);
  const [body, setBody] = useState(PRESETS[0].body);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const handleSelectPreset = (idx: number) => {
    setSelectedPreset(idx);
    setName(PRESETS[idx].name);
    setEmail(PRESETS[idx].email);
    setSubject(PRESETS[idx].subject);
    setBody(PRESETS[idx].body);
    setResult(null);
    setError(null);
  };

  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.simulateEmail({
        sender_name: name.trim(),
        sender_email: email.trim(),
        subject: subject.trim(),
        body: body.trim(),
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Simulation request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-2xl w-full p-6 sm:p-8 my-8 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">Simulate Inbound Customer Email</h2>
            <p className="text-xs text-slate-500">Test policy matching, triage logic, automated drafting, and escalation</p>
          </div>
        </div>

        {/* Preset Selector */}
        <div className="mt-4 mb-5">
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            Quick Test Scenarios
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {PRESETS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectPreset(idx)}
                className={`text-left p-2.5 rounded-lg border text-xs transition ${
                  selectedPreset === idx
                    ? 'border-emerald-600 bg-emerald-50 text-emerald-900 font-medium shadow-xs'
                    : 'border-slate-200 hover:border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-xs flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result ? (
          <div className="space-y-4 animate-in fade-in duration-200">
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-600 uppercase">Triage Result</span>
                {result.decision.action === 'escalate' ? (
                  <span className="px-2.5 py-1 rounded text-xs font-semibold bg-amber-100 text-amber-800 flex items-center space-x-1">
                    <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Escalated to Human
                  </span>
                ) : (
                  <span className="px-2.5 py-1 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Automated Reply Drafted
                  </span>
                )}
              </div>

              <div className="text-xs text-slate-700 space-y-1">
                <div>
                  <span className="font-semibold text-slate-900">Policy Section: </span>
                  <span className="font-mono bg-slate-200 px-1.5 py-0.5 rounded text-[11px]">
                    {result.decision.section}
                  </span>
                </div>
                <div>
                  <span className="font-semibold text-slate-900">Reason: </span>
                  {result.decision.reason}
                </div>
                {result.decision.proposed_action && (
                  <div>
                    <span className="font-semibold text-slate-900">Proposed Action: </span>
                    <span className="font-mono text-emerald-700 font-semibold">
                      {result.decision.proposed_action}
                    </span>
                  </div>
                )}
              </div>

              {result.decision.reply && (
                <div className="mt-3">
                  <div className="text-xs font-semibold text-slate-900 mb-1">Generated Response:</div>
                  <pre className="text-xs bg-white p-3 rounded border border-slate-200 text-slate-800 whitespace-pre-wrap font-sans">
                    {result.decision.reply}
                  </pre>
                </div>
              )}
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setResult(null)}
                className="px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition"
              >
                Test Another Message
              </button>
              <button
                type="button"
                onClick={() => {
                  onSuccess(result.ticket_id);
                  onClose();
                }}
                className="px-4 py-2 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg flex items-center space-x-1 shadow-sm transition"
              >
                <span>View Created Ticket</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleRunSimulation} className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Customer Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Customer Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Subject</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Message Body</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={4}
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500 font-sans"
              />
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg flex items-center space-x-1.5 shadow-sm transition disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{loading ? 'Evaluating Policy...' : 'Run Simulation'}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
