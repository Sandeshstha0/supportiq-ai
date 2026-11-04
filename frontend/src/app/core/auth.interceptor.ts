import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { API_BASE_URL, AUTH_ENDPOINTS } from './api.config';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.getToken();
  const isApiRequest = request.url.startsWith(API_BASE_URL);
  const isLoginRequest = request.url === AUTH_ENDPOINTS.login;
  const outgoing = isApiRequest && token && !isLoginRequest
    ? request.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : request;

  return next(outgoing).pipe(catchError(error => {
    if (error.status === 401 && isApiRequest && !isLoginRequest && token) {
      auth.logout();
      void router.navigate(['/admin/login'], { queryParams: { reason: 'expired' } });
    }
    return throwError(() => error);
  }));
};
