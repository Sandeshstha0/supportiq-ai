import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../core/api.config';

export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed';

export interface StaffTicket {
  id: number;
  guest_session_id: number | null;
  category: string;
  subject: string;
  description: string;
  status: TicketStatus;
  decision: string | null;
  customer_name: string | null;
  customer_email: string | null;
  customer_phone: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface TicketListResponse {
  items: StaffTicket[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TicketQuery {
  search: string;
  status?: TicketStatus;
  category?: string;
  page: number;
  pageSize: number;
}

export interface TicketDecisionResponse {
  message: string;
  email_notification_sent: boolean;
  ticket: StaffTicket;
}

@Injectable({ providedIn: 'root' })
export class TicketService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/tickets`;

  getTickets(query: TicketQuery): Observable<TicketListResponse> {
    let params = new HttpParams()
      .set('page', query.page)
      .set('page_size', query.pageSize);
    if (query.search.trim()) params = params.set('search', query.search.trim());
    if (query.status) params = params.set('status_filter', query.status);
    if (query.category) params = params.set('category', query.category);
    return this.http.get<TicketListResponse>(`${this.baseUrl}/staff/all`, { params });
  }

  getTicket(ticketId: number): Observable<StaffTicket> {
    return this.http.get<StaffTicket>(`${this.baseUrl}/staff/${ticketId}`);
  }

  updateDecision(ticketId: number, decision: string, status: TicketStatus): Observable<TicketDecisionResponse> {
    return this.http.patch<TicketDecisionResponse>(`${this.baseUrl}/${ticketId}/decision`, { decision, status });
  }
}
