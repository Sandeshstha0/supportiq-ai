
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ChatRequest {
  message: string;
  conversation_id?: number;
  session_token: string;
}

export interface ChatResponse {
  reply: string;
  assistant: string;
  conversation_id: number;
}

export interface Conversation {
  conversation_id: number;
  title: string;
  last_message: string;
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ConversationMessagesResponse {
  conversation_id: number;
  messages: ConversationMessage[];
}

export interface GuestSessionResponse {
  session_token: string;
  session_id: number;
  expires_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private http = inject(HttpClient);

  private readonly apiUrl = 'http://127.0.0.1:8000/api/v1/chat';
  private readonly guestUrl = 'http://127.0.0.1:8000/api/v1/guest';

  createOrGetGuestSession(
    sessionToken?: string
  ): Observable<GuestSessionResponse> {
    return this.http.post<GuestSessionResponse>(
      `${this.guestUrl}/session`,
      null,
      {
        params: sessionToken ? { session_token: sessionToken } : {}
      }
    );
  }

  private getSessionHeaders(sessionToken: string): HttpHeaders {
    return new HttpHeaders({
      'X-Guest-Session': sessionToken
    });
  }

  sendMessage(request: ChatRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(
      this.apiUrl,
      request
    );
  }

  getConversations(
    sessionToken: string
  ): Observable<{ conversations: Conversation[] }> {
    return this.http.get<{ conversations: Conversation[] }>(
      `${this.apiUrl}/conversations`,
      {
        headers: this.getSessionHeaders(sessionToken)
      }
    );
  }

  getConversationMessages(
    conversationId: number,
    sessionToken: string
  ): Observable<ConversationMessagesResponse> {
    return this.http.get<ConversationMessagesResponse>(
      `${this.apiUrl}/conversations/${conversationId}`,
      {
        headers: this.getSessionHeaders(sessionToken)
      }
    );
  }

  deleteConversation(
    conversationId: number,
    sessionToken: string
  ): Observable<{ message: string; conversation_id: number }> {
    return this.http.delete<{
      message: string;
      conversation_id: number;
    }>(
      `${this.apiUrl}/conversations/${conversationId}`,
      {
        headers: this.getSessionHeaders(sessionToken)
      }
    );
  }
}
