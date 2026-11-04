import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../core/api.config';

export interface CustomerDirectoryItem {
  customer_id: number;
  identity_type: 'guest_session';
  name: string | null;
  phone: string | null;
  email: string | null;
  location: string | null;
  first_seen: string;
  order_count: number;
  ticket_count: number;
  conversation_count: number;
}

export interface CustomerDirectoryResponse {
  items: CustomerDirectoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: {
    total_guest_sessions: number;
    sessions_with_orders: number;
    sessions_with_tickets: number;
  };
  identity_note: string;
}

export interface CustomerOrderHistory {
  id: number;
  customer_name: string;
  customer_phone: string;
  customer_email: string | null;
  delivery_location: string;
  ward_number: number;
  total_amount: number;
  status: string;
  created_at: string;
}

export interface CustomerTicketHistory {
  id: number;
  customer_name: string | null;
  customer_email: string | null;
  customer_phone: string | null;
  category: string;
  subject: string;
  status: string;
  created_at: string;
}

export interface CustomerConversationMessage {
  role: string;
  content: string;
  created_at: string;
}

export interface CustomerConversationHistory {
  id: number;
  created_at: string;
  message_count: number;
  messages: CustomerConversationMessage[];
}

export interface CustomerDetails extends CustomerDirectoryItem {
  expires_at: string;
  orders: CustomerOrderHistory[];
  tickets: CustomerTicketHistory[];
  conversations: CustomerConversationHistory[];
  activity: { type: string; record_id: number; occurred_at: string; summary: string }[];
}

@Injectable({ providedIn: 'root' })
export class CustomerService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/customers/staff`;

  getCustomers(search: string, page: number, pageSize: number): Observable<CustomerDirectoryResponse> {
    let params = new HttpParams().set('page', page).set('page_size', pageSize);
    if (search.trim()) params = params.set('search', search.trim());
    return this.http.get<CustomerDirectoryResponse>(`${this.baseUrl}/all`, { params });
  }

  getCustomer(customerId: number): Observable<CustomerDetails> {
    return this.http.get<CustomerDetails>(`${this.baseUrl}/${customerId}`);
  }
}
