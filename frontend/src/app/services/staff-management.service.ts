import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../core/api.config';

export type StaffRole = 'admin' | 'staff';
export interface StaffAccount {
  id: number;
  username: string;
  email: string;
  role: StaffRole;
  is_active: boolean;
  created_at: string;
  is_last_active_admin: boolean;
}
export interface StaffDirectory {
  items: StaffAccount[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  active_admin_count: number;
}
export interface StaffMutationResponse { message: string; staff: StaffAccount; }

@Injectable({ providedIn: 'root' })
export class StaffManagementService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/auth/staff`;

  list(search: string, page: number, pageSize: number): Observable<StaffDirectory> {
    let params = new HttpParams().set('page', page).set('page_size', pageSize);
    if (search.trim()) params = params.set('search', search.trim());
    return this.http.get<StaffDirectory>(this.baseUrl, { params });
  }
  get(staffId: number): Observable<StaffAccount> {
    return this.http.get<StaffAccount>(`${this.baseUrl}/${staffId}`);
  }
  create(values: { username: string; email: string; password: string }): Observable<StaffMutationResponse> {
    return this.http.post<StaffMutationResponse>(this.baseUrl, { ...values, role: 'staff' });
  }
  update(staffId: number, values: { username: string; email: string; role: StaffRole }): Observable<StaffMutationResponse> {
    return this.http.patch<StaffMutationResponse>(`${this.baseUrl}/${staffId}`, values);
  }
  setActive(staffId: number, isActive: boolean): Observable<StaffMutationResponse> {
    const params = new HttpParams().set('is_active', isActive);
    return this.http.patch<StaffMutationResponse>(`${this.baseUrl}/${staffId}/status`, null, { params });
  }
}
