import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../core/api.config';

export interface StaffConversation {
  id: number; guest_session_id: number | null; created_at: string; latest_activity_at: string;
  message_count: number; preview: string | null; has_customer_profile: boolean;
}
export interface StaffConversationPage {
  items: StaffConversation[]; total: number; page: number; page_size: number; total_pages: number;
}
export interface StaffConversationMessage { id: number; role: string; content: string; created_at: string; }
export interface StaffConversationDetails extends StaffConversation { messages: StaffConversationMessage[]; }

@Injectable({ providedIn: 'root' })
export class ConversationService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/conversations/staff`;

  list(search: string, dateFrom: string, dateTo: string, page: number, pageSize: number): Observable<StaffConversationPage> {
    let params = new HttpParams().set('page', page).set('page_size', pageSize);
    if (search.trim()) params = params.set('search', search.trim());
    if (dateFrom) params = params.set('date_from', dateFrom);
    if (dateTo) params = params.set('date_to', dateTo);
    return this.http.get<StaffConversationPage>(`${this.baseUrl}/all`, { params });
  }

  get(conversationId: number): Observable<StaffConversationDetails> {
    return this.http.get<StaffConversationDetails>(`${this.baseUrl}/${conversationId}`);
  }
}
