/**
 * Typed API client for ResolveHelm Admin Backend.
 */

export interface EventItem {
  id: string;
  message_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'retrying';
  attempts: number;
  error?: string | null;
  result?: {
    action?: string;
    section?: string;
    proposed_action?: string;
    reason?: string;
  } | null;
  created_at: string;
  completed_at?: string | null;
}

export interface TicketItem {
  id: string;
  thread_id: string;
  customer: string;
  subject: string;
  category: string;
  status: 'open' | 'answered' | 'escalated' | 'closed';
  proposed_action?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageItem {
  id: string;
  ticket_id: string;
  message_id: string;
  direction: 'incoming' | 'outgoing';
  sender: string;
  recipient: string;
  body: string;
  created_at: string;
}

export interface KBEntry {
  id: string;
  section: string;
  title: string;
  content: string;
  updated_at: string;
}

class ApiClient {
  private authHeader: string | null = null;

  setCredentials(user: string, pass: string) {
    this.authHeader = 'Basic ' + btoa(`${user}:${pass}`);
    sessionStorage.setItem('rh_auth', this.authHeader);
  }

  loadSavedCredentials(): boolean {
    const saved = sessionStorage.getItem('rh_auth');
    if (saved) {
      this.authHeader = saved;
      return true;
    }
    return false;
  }

  clearCredentials() {
    this.authHeader = null;
    sessionStorage.removeItem('rh_auth');
  }

  isAuthenticated(): boolean {
    return !!this.authHeader;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    if (this.authHeader) {
      headers.set('Authorization', this.authHeader);
    }
    headers.set('Accept', 'application/json');

    const res = await fetch(endpoint, { ...options, headers });
    if (res.status === 401) {
      this.clearCredentials();
      throw new Error('Unauthorized: Please log in');
    }
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errBody.detail || `Request failed with code ${res.status}`);
    }
    return res.json();
  }

  async verifyAuth(): Promise<{ status: string; user: string }> {
    return this.request('/api/login');
  }

  async getEvents(limit = 50, offset = 0): Promise<EventItem[]> {
    return this.request(`/api/events?limit=${limit}&offset=${offset}`);
  }

  async getTickets(limit = 50, offset = 0): Promise<TicketItem[]> {
    return this.request(`/api/tickets?limit=${limit}&offset=${offset}`);
  }

  async getTicketMessages(ticketId: string): Promise<MessageItem[]> {
    return this.request(`/api/tickets/${ticketId}/messages`);
  }

  async getKnowledgeBase(): Promise<KBEntry[]> {
    return this.request('/api/knowledge-base');
  }

  async updateKnowledgeBase(id: string, title: string, content: string): Promise<{ status: string; entry: KBEntry }> {
    return this.request(`/api/knowledge-base/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content }),
    });
  }

  async triggerPoll(): Promise<{ status: string; processed: number }> {
    return this.request('/api/poll', { method: 'POST' });
  }
}

export const api = new ApiClient();
