import React, { useState } from 'react';
import { KBEntry, api } from '../api';
import { BookOpen, Save, Check, AlertCircle } from 'lucide-react';

interface KnowledgeBasePageProps {
  entries: KBEntry[];
  onRefresh: () => void;
}

export const KnowledgeBasePage: React.FC<KnowledgeBasePageProps> = ({ entries, onRefresh }) => {
  const [selectedEntry, setSelectedEntry] = useState<KBEntry | null>(entries[0] || null);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSelect = (entry: KBEntry) => {
    setSelectedEntry(entry);
    setEditTitle(entry.title);
    setEditContent(entry.content);
    setSaveSuccess(false);
    setSaveError(null);
  };

  const handleSave = async () => {
    if (!selectedEntry) return;
    setSaving(true);
    setSaveSuccess(false);
    setSaveError(null);

    try {
      const res = await api.updateKnowledgeBase(selectedEntry.id, editTitle, editContent);
      setSelectedEntry(res.entry);
      setSaveSuccess(true);
      onRefresh();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to update knowledge base entry.');
    } finally {
      setSaving(false);
    }
  };

  // Group entries by section
  const sections = Array.from(new Set(entries.map((e) => e.section)));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Knowledge Base Management</h1>
        <p className="text-sm text-slate-500">
          Authoritative business policies, product specs, and deterministic escalation rules.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Navigation Sidebar */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm h-[700px] overflow-y-auto p-4 space-y-6">
          {sections.map((sec) => {
            const secEntries = entries.filter((e) => e.section === sec);
            return (
              <div key={sec} className="space-y-1">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider px-2 mb-2">
                  {sec}
                </h3>
                {secEntries.map((entry) => (
                  <button
                    key={entry.id}
                    onClick={() => handleSelect(entry)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition ${
                      selectedEntry?.id === entry.id
                        ? 'bg-emerald-50 text-emerald-900 font-semibold'
                        : 'text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {entry.title}
                  </button>
                ))}
              </div>
            );
          })}
        </div>

        {/* Editor Form */}
        <div className="md:col-span-2 bg-white border border-slate-200 rounded-xl shadow-sm p-6 flex flex-col h-[700px]">
          {selectedEntry ? (
            <div className="flex flex-col h-full space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono">
                  Section: {selectedEntry.section}
                </span>

                <div className="flex items-center space-x-3">
                  {saveSuccess && (
                    <span className="text-xs text-emerald-600 font-medium flex items-center space-x-1">
                      <Check className="w-4 h-4" /> <span>Changes saved to database</span>
                    </span>
                  )}
                  {saveError && (
                    <span className="text-xs text-red-600 font-medium flex items-center space-x-1">
                      <AlertCircle className="w-4 h-4" /> <span>{saveError}</span>
                    </span>
                  )}
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg shadow-sm flex items-center space-x-1.5 transition disabled:opacity-50"
                  >
                    <Save className="w-4 h-4" />
                    <span>{saving ? 'Saving...' : 'Save Policy'}</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Entry Title
                </label>
                <input
                  type="text"
                  value={editTitle || selectedEntry.title}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex-1 flex flex-col">
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Markdown Policy Content
                </label>
                <textarea
                  value={editContent || selectedEntry.content}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="flex-1 w-full p-4 border border-slate-300 rounded-lg font-mono text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
                  placeholder="Enter policy markdown instructions..."
                />
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
              <BookOpen className="w-8 h-8" />
              <p>Select a policy entry on the left to edit.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
