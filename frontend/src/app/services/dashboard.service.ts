import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../core/api.config';

export interface DashboardStats {
  total_tickets: number;
  open_tickets: number;
  in_progress_tickets: number;
  resolved_tickets: number;
  closed_tickets: number;
}

export interface DashboardTicket {
  id: number;
  customer_name: string | null;
  subject: string;
  category: string;
  status: string;
  created_at: string;
}

export interface CategoryStat {
  category: string;
  total: number;
}

export interface StatusStat {
  status: string;
  total: number;
  percentage: number;
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/dashboard`;

  getStats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>(`${this.baseUrl}/stats`);
  }

  getRecentTickets(): Observable<DashboardTicket[]> {
    return this.http.get<DashboardTicket[]>(`${this.baseUrl}/recent-tickets`);
  }

  getCategoryStats(): Observable<CategoryStat[]> {
    return this.http.get<CategoryStat[]>(`${this.baseUrl}/category-stats`);
  }

  getStatusDistribution(): Observable<StatusStat[]> {
    return this.http.get<StatusStat[]>(`${this.baseUrl}/status-distribution`);
  }
}
