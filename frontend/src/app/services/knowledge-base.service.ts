import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../core/api.config';

export interface KnowledgeDocument {
  id: string;
  title: string;
  source: string;
  filename: string | null;
  created_at: string | null;
  indexing_status: string;
  legacy: boolean;
  chunk_count: number;
  preview: string;
}
export interface KnowledgeDocumentPage {
  items: KnowledgeDocument[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
export interface KnowledgeDocumentDetails extends KnowledgeDocument {
  chunks: { index: number; text: string }[];
}
export interface KnowledgeMutationResult {
  success: boolean;
  document_id: string;
  title: string;
  source: string;
  filename: string | null;
  created_at: string;
  chunks_stored: number;
  indexing_status: string;
  message: string;
}

@Injectable({ providedIn: 'root' })
export class KnowledgeBaseService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/knowledge/staff/documents`;

  list(search: string, page: number, pageSize: number): Observable<KnowledgeDocumentPage> {
    let params = new HttpParams().set('page', page).set('page_size', pageSize);
    if (search.trim()) params = params.set('search', search.trim());
    return this.http.get<KnowledgeDocumentPage>(this.baseUrl, { params });
  }
  get(id: string): Observable<KnowledgeDocumentDetails> {
    return this.http.get<KnowledgeDocumentDetails>(`${this.baseUrl}/${encodeURIComponent(id)}`);
  }
  upload(file: File): Observable<KnowledgeMutationResult> {
    const body = new FormData(); body.append('file', file, file.name);
    return this.http.post<KnowledgeMutationResult>(`${this.baseUrl}/upload`, body);
  }
  replace(id: string, file: File): Observable<KnowledgeMutationResult> {
    const body = new FormData(); body.append('file', file, file.name);
    return this.http.put<KnowledgeMutationResult>(`${this.baseUrl}/${encodeURIComponent(id)}`, body);
  }
  delete(id: string): Observable<{ success: boolean; document_id: string; message: string }> {
    return this.http.delete<{ success: boolean; document_id: string; message: string }>(`${this.baseUrl}/${encodeURIComponent(id)}`);
  }
}
