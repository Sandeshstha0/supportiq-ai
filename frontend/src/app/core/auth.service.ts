import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { inject, Injectable, PLATFORM_ID, signal } from '@angular/core';
import { Observable, catchError, map, of, tap } from 'rxjs';
import { AUTH_ENDPOINTS } from './api.config';

export interface StaffProfile {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'staff' | string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  email: string;
  role: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly storageKey = 'supportiq_staff_token';
  readonly currentUser = signal<StaffProfile | null>(null);

  login(username: string, password: string): Observable<StaffProfile> {
    return this.http.post<LoginResponse>(AUTH_ENDPOINTS.login, { username, password }).pipe(
      tap(response => this.storeToken(response.access_token)),
      map(response => ({
        id: response.user_id,
        username: response.username,
        email: response.email,
        role: response.role,
        is_active: true,
      })),
      tap(user => this.currentUser.set(user)),
    );
  }

  restoreSession(): Observable<StaffProfile | null> {
    if (!this.getToken()) {
      this.currentUser.set(null);
      return of(null);
    }

    return this.http.get<StaffProfile>(AUTH_ENDPOINTS.me).pipe(
      tap(user => this.currentUser.set(user)),
      catchError(() => {
        this.clearSession();
        return of(null);
      }),
    );
  }

  getToken(): string | null {
    if (!isPlatformBrowser(this.platformId)) return null;
    try {
      return window.sessionStorage.getItem(this.storageKey);
    } catch {
      return null;
    }
  }

  logout(): void {
    this.clearSession();
  }

  private storeToken(token: string): void {
    if (!isPlatformBrowser(this.platformId)) return;
    try {
      window.sessionStorage.setItem(this.storageKey, token);
    } catch {
      this.currentUser.set(null);
      throw new Error('Browser session storage is unavailable.');
    }
  }

  private clearSession(): void {
    if (isPlatformBrowser(this.platformId)) {
      try {
        window.sessionStorage.removeItem(this.storageKey);
      } catch {
        // The in-memory user state is still cleared if storage is unavailable.
      }
    }
    this.currentUser.set(null);
  }
}
