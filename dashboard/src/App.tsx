import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { LoginModal } from './components/LoginModal';
import { EventsPage } from './pages/EventsPage';
import { TicketsPage } from './pages/TicketsPage';
import { KnowledgeBasePage } from './pages/KnowledgeBasePage';
import { api, EventItem, TicketItem, KBEntry } from './api';

export const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentTab, setCurrentTab] = useState<'events' | 'tickets' | 'kb'>('events');
  const [events, setEvents] = useState<EventItem[]>([]);
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [kbEntries, setKbEntries] = useState<KBEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    if (api.loadSavedCredentials()) {
      setIsAuthenticated(true);
      loadAllData();
    }
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [evs, tks, kbs] = await Promise.all([
        api.getEvents().catch(() => []),
        api.getTickets().catch(() => []),
        api.getKnowledgeBase().catch(() => []),
      ]);
      setEvents(evs);
      setTickets(tks);
      setKbEntries(kbs);
    } catch (e) {
      console.error('Error fetching dashboard data:', e);
    } finally {
      setLoading(false);
    }
  };

  const handlePoll = async () => {
    setIsPolling(true);
    try {
      await api.triggerPoll();
      await loadAllData();
    } catch (e) {
      console.error('Manual poll failed:', e);
    } finally {
      setIsPolling(false);
    }
  };

  const handleLogout = () => {
    api.clearCredentials();
    setIsAuthenticated(false);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {!isAuthenticated && <LoginModal onSuccess={() => { setIsAuthenticated(true); loadAllData(); }} />}

      <Navbar
        currentTab={currentTab}
        setTab={setCurrentTab}
        onLogout={handleLogout}
        onPoll={handlePoll}
        isPolling={isPolling}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentTab === 'events' && (
          <EventsPage events={events} loading={loading} onRefresh={loadAllData} />
        )}
        {currentTab === 'tickets' && (
          <TicketsPage tickets={tickets} loading={loading} onRefresh={loadAllData} />
        )}
        {currentTab === 'kb' && (
          <KnowledgeBasePage entries={kbEntries} onRefresh={loadAllData} />
        )}
      </main>
    </div>
  );
};
