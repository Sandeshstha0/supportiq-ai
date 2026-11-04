import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../core/api.config';

export type OrderStatus =
  | 'pending_confirmation'
  | 'confirmed'
  | 'processing'
  | 'out_for_delivery'
  | 'delivered'
  | 'cancelled';

export interface OrderItem {
  id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface CustomerOrder {
  id: number;
  customer_name: string;
  customer_phone: string;
  customer_email: string | null;
  delivery_location: string;
  ward_number: number;
  total_amount: number;
  status: OrderStatus;
  created_at: string;
  items: OrderItem[];
}

export interface OrderListResponse {
  items: CustomerOrder[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface OrderQuery {
  search?: string;
  status?: OrderStatus;
  page: number;
  page_size: number;
}

@Injectable({ providedIn: 'root' })
export class OrderService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/orders/staff`;

  getOrders(query: OrderQuery): Observable<OrderListResponse> {
    let params = new HttpParams()
      .set('page', query.page)
      .set('page_size', query.page_size);
    if (query.search?.trim()) params = params.set('search', query.search.trim());
    if (query.status) params = params.set('status', query.status);
    return this.http.get<OrderListResponse>(`${this.baseUrl}/all`, { params });
  }

  getOrder(orderId: number): Observable<CustomerOrder> {
    return this.http.get<CustomerOrder>(`${this.baseUrl}/${orderId}`);
  }

  updateStatus(orderId: number, status: OrderStatus): Observable<CustomerOrder> {
    return this.http.patch<CustomerOrder>(`${this.baseUrl}/${orderId}/status`, { status });
  }
}
