import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../core/api.config';

export interface ManagedProduct {
  id: number;
  name: string;
  category: string;
  price: number;
  unit: string;
  stock: number;
  description: string;
  brand: string;
  has_order_history: boolean;
}
export interface ManagedProductPage {
  items: ManagedProduct[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  categories: string[];
}
export interface ProductInput {
  name: string;
  category: string;
  price: number;
  unit: string;
  stock: number;
  description: string;
  brand: string;
}

@Injectable({ providedIn: 'root' })
export class ProductManagementService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${API_BASE_URL}/products/staff`;

  list(search: string, category: string, availability: string, page: number, pageSize: number): Observable<ManagedProductPage> {
    let params = new HttpParams().set('page', page).set('page_size', pageSize);
    if (search.trim()) params = params.set('search', search.trim());
    if (category) params = params.set('category', category);
    if (availability) params = params.set('availability', availability);
    return this.http.get<ManagedProductPage>(`${this.baseUrl}/all`, { params });
  }
  get(productId: number): Observable<ManagedProduct> {
    return this.http.get<ManagedProduct>(`${this.baseUrl}/${productId}`);
  }
  create(product: ProductInput): Observable<ManagedProduct> {
    return this.http.post<ManagedProduct>(this.baseUrl, product);
  }
  update(productId: number, product: Omit<ProductInput, 'stock'>): Observable<ManagedProduct> {
    return this.http.patch<ManagedProduct>(`${this.baseUrl}/${productId}`, product);
  }
  updateStock(productId: number, stock: number): Observable<ManagedProduct> {
    return this.http.patch<ManagedProduct>(`${this.baseUrl}/${productId}/stock`, { stock });
  }
  delete(productId: number): Observable<{ success: boolean; product_id: number; message: string }> {
    return this.http.delete<{ success: boolean; product_id: number; message: string }>(`${this.baseUrl}/${productId}`);
  }
}
